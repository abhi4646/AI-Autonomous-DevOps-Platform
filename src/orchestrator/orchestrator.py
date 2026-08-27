from src.ai.decision_engine import DecisionEngine
from src.policy.decision_policy import DecisionPolicy
from src.safety.guardrails import SafetyGuardrails
from src.approval.approval_manager import ApprovalManager
from src.audit.audit_logger import AuditLogger
from src.persistence.database import Database

from src.intelligence.context_builder import (
    DecisionContextBuilder,
)
from src.intelligence.recommender import (
    RecommendationEngine,
)


class Orchestrator:
    def __init__(self, database=None):
        """
        Main orchestration layer for the Autonomous DevOps Platform.

        Decision intelligence augments the existing deterministic
        routing, policy, and safety layers. It never bypasses
        SafetyGuardrails or human approval controls.
        """

        self.agents = []

        # ---------------------------------------------------------
        # PERSISTENCE
        # ---------------------------------------------------------

        self.database = database or Database()

        # ---------------------------------------------------------
        # PLATFORM COMPONENTS
        # ---------------------------------------------------------

        self.decision_engine = DecisionEngine()
        self.decision_policy = DecisionPolicy()
        self.safety_guardrails = SafetyGuardrails()

        self.approval_manager = ApprovalManager(
            database=self.database
        )

        self.audit_logger = AuditLogger(
            database=self.database
        )

        # ---------------------------------------------------------
        # DECISION INTELLIGENCE
        # ---------------------------------------------------------

        self.context_builder = DecisionContextBuilder(
            database=self.database
        )

        self.recommendation_engine = RecommendationEngine()

    def register_agent(self, agent):
        """Register an agent with the orchestrator."""
        self.agents.append(agent)

    def run(self, context=None):
        """Run all registered agents."""
        return {
            agent.name: agent.execute(context)
            for agent in self.agents
        }

    def _requires_human_approval(
        self,
        request,
        safety_result,
        intelligence_result=None,
    ):
        """
        Determine whether a mutating operation requires human
        approval.

        Existing safety controls remain authoritative.

        Decision intelligence may increase conservatism by
        requiring approval, but it may never bypass an approval
        required by the existing safety layer.
        """

        request_lower = request.lower()

        approval_keywords = [
            "deploy",
            "apply",
            "delete",
            "destroy",
            "remove",
            "restart",
            "terminate",
            "scale",
            "rollback",
            "update",
            "modify",
            "change",
            "create",
            "push",
            "merge",
            "write",
        ]

        mutating_request = any(
            keyword in request_lower
            for keyword in approval_keywords
        )

        if not mutating_request:
            return False

        safety_action = safety_result.get(
            "action",
            "execute",
        )

        safety_requires_approval = (
            safety_action
            in {
                "review",
                "escalate",
            }
        )

        intelligence_requires_approval = False

        if intelligence_result is not None:
            intelligence_requires_approval = bool(
                intelligence_result.get(
                    "requires_approval",
                    False,
                )
            )

        return (
            safety_requires_approval
            or intelligence_requires_approval
        )

    def _build_intelligence(
        self,
        request,
        selected_agent,
        decision,
        context,
    ):
        """
        Build operational decision context and produce an
        explainable intelligence recommendation.

        Runtime context may optionally provide:

        - environment
        - incident_id
        - health_result
        - metadata

        Existing callers that provide no intelligence-specific
        context remain supported.
        """

        runtime_context = dict(
            context or {}
        )

        environment = runtime_context.get(
            "environment",
            "unknown",
        )

        incident_id = runtime_context.get(
            "incident_id"
        )

        health_result = runtime_context.get(
            "health_result"
        )

        metadata = runtime_context.get(
            "metadata"
        )

        decision_context = self.context_builder.build(
            request,
            agent=selected_agent,
            environment=environment,
            routing_confidence=decision.get(
                "confidence",
                0.0,
            ),
            incident_id=incident_id,
            health_result=health_result,
            metadata=metadata,
        )

        recommendation = (
            self.recommendation_engine
            .recommend(
                decision_context
            )
        )

        return {
            "context": decision_context.to_dict(),
            "recommendation": recommendation,
        }

    def route(
        self,
        request,
        context=None,
        approval_id=None,
    ):
        """
        Route a request through:

        DecisionEngine
        -> Decision Intelligence
        -> DecisionPolicy
        -> SafetyGuardrails
        -> Human Approval
        -> Agent Execution
        -> Persistence
        -> Audit Logging
        """

        if not request:
            raise ValueError(
                "Request cannot be empty"
            )

        # ---------------------------------------------------------
        # 1. AI ROUTING DECISION
        # ---------------------------------------------------------

        decision = (
            self.decision_engine
            .decide_agents(request)
        )

        if not decision["matched"]:
            self.audit_logger.log(
                request=request,
                action="no_route",
                allowed=False,
                risk="low",
                reason="No suitable agent found",
            )

            return {
                "status": "no_route",
                "request": request,
                "message": (
                    "No suitable agent found"
                ),
            }

        recommended_agents = (
            decision["recommended_agents"]
        )

        if not recommended_agents:
            self.audit_logger.log(
                request=request,
                action="no_route",
                allowed=False,
                risk="low",
                reason="No suitable agent found",
            )

            return {
                "status": "no_route",
                "request": request,
                "message": (
                    "No suitable agent found"
                ),
            }

        selected_agent = (
            recommended_agents[0]
        )

        # ---------------------------------------------------------
        # 2. DECISION INTELLIGENCE
        # ---------------------------------------------------------

        intelligence = self._build_intelligence(
            request=request,
            selected_agent=selected_agent,
            decision=decision,
            context=context,
        )

        intelligence_result = intelligence[
            "recommendation"
        ]

        # ---------------------------------------------------------
        # 3. EXISTING DECISION POLICY
        # ---------------------------------------------------------

        policy_result = (
            self.decision_policy
            .evaluate(decision)
        )

        # ---------------------------------------------------------
        # 4. EXISTING SAFETY GUARDRAILS
        # ---------------------------------------------------------

        safety_result = (
            self.safety_guardrails
            .evaluate(
                request,
                policy_result=policy_result,
            )
        )

        safety_action = safety_result.get(
            "action",
            "execute",
        )

        risk = safety_result.get(
            "risk",
            "low",
        )

        reason = safety_result.get(
            "reason",
            "",
        )

        # ---------------------------------------------------------
        # 5. HARD SAFETY BLOCK
        # ---------------------------------------------------------

        if safety_action == "block":
            self.audit_logger.log(
                request=request,
                action="block",
                agent=selected_agent,
                allowed=False,
                risk=risk,
                reason=reason,
                metadata={
                    "decision": decision,
                    "intelligence": intelligence,
                    "policy": policy_result,
                    "safety": safety_result,
                },
            )

            return {
                "status": "blocked",
                "request": request,
                "agent": selected_agent,
                "risk": risk,
                "message": reason,
                "intelligence": intelligence_result,
            }

        # ---------------------------------------------------------
        # 6. HUMAN APPROVAL
        # ---------------------------------------------------------

        if self._requires_human_approval(
            request,
            safety_result,
            intelligence_result,
        ):

            if approval_id is None:
                approval = (
                    self.approval_manager
                    .create_request(
                        request=request,
                        action=safety_action,
                        agent=selected_agent,
                        risk=risk,
                        metadata={
                            "decision": decision,
                            "intelligence": intelligence,
                            "policy": policy_result,
                            "safety": safety_result,
                        },
                    )
                )

                self.audit_logger.log(
                    request=request,
                    action="approval_requested",
                    agent=selected_agent,
                    allowed=False,
                    risk=risk,
                    reason=(
                        intelligence_result.get(
                            "explanation"
                        )
                        or reason
                    ),
                    metadata={
                        "approval_id": approval[
                            "approval_id"
                        ],
                        "intelligence": intelligence,
                    },
                )

                return {
                    "status": "pending_approval",
                    "request": request,
                    "agent": selected_agent,
                    "risk": risk,
                    "approval_id": approval[
                        "approval_id"
                    ],
                    "intelligence": intelligence_result,
                    "message": (
                        "Human approval required "
                        "before execution"
                    ),
                }

            approval = (
                self.approval_manager
                .get_request(
                    approval_id
                )
            )

            if approval is None:
                return {
                    "status": (
                        "approval_not_found"
                    ),
                    "request": request,
                    "agent": selected_agent,
                    "approval_id": approval_id,
                    "intelligence": intelligence_result,
                    "message": (
                        "Approval request was "
                        "not found"
                    ),
                }

            if (
                approval["status"]
                == "pending"
            ):
                return {
                    "status": (
                        "pending_approval"
                    ),
                    "request": request,
                    "agent": selected_agent,
                    "risk": risk,
                    "approval_id": approval_id,
                    "intelligence": intelligence_result,
                    "message": (
                        "Approval is still pending"
                    ),
                }

            if (
                approval["status"]
                == "rejected"
            ):
                self.audit_logger.log(
                    request=request,
                    action="rejected",
                    agent=selected_agent,
                    allowed=False,
                    risk=risk,
                    reason=(
                        approval.get(
                            "reason"
                        )
                        or (
                            "Human rejected "
                            "request"
                        )
                    ),
                    metadata={
                        "approval_id": (
                            approval_id
                        ),
                        "decided_by": (
                            approval.get(
                                "decided_by"
                            )
                        ),
                        "intelligence": intelligence,
                    },
                )

                return {
                    "status": "rejected",
                    "request": request,
                    "agent": selected_agent,
                    "approval_id": approval_id,
                    "intelligence": intelligence_result,
                    "message": (
                        "Human approval was "
                        "rejected"
                    ),
                }

            if not (
                self.approval_manager
                .can_execute(
                    approval_id
                )
            ):
                return {
                    "status": (
                        "pending_approval"
                    ),
                    "request": request,
                    "agent": selected_agent,
                    "approval_id": approval_id,
                    "intelligence": intelligence_result,
                    "message": (
                        "Request is not approved "
                        "for execution"
                    ),
                }

        # ---------------------------------------------------------
        # 7. LOCATE AND EXECUTE SELECTED AGENT
        # ---------------------------------------------------------

        for agent in self.agents:
            if (
                agent.name.lower()
                == selected_agent
            ):

                try:
                    execution_context = dict(
                        context or {}
                    )

                    execution_context[
                        "request"
                    ] = request

                    execution_context[
                        "decision_intelligence"
                    ] = intelligence_result

                    result = agent.execute(
                        execution_context
                    )

                    self.database.save_execution(
                        request=request,
                        agent=agent.name,
                        status="success",
                        result=result,
                    )

                    self.audit_logger.log(
                        request=request,
                        action="execute",
                        agent=agent.name,
                        allowed=True,
                        risk=risk,
                        reason=(
                            "Request executed "
                            "successfully"
                        ),
                        metadata={
                            "decision": decision,
                            "intelligence": intelligence,
                            "policy": policy_result,
                            "safety": safety_result,
                            "approval_id": (
                                approval_id
                            ),
                        },
                    )

                    return {
                        "status": "routed",
                        "request": request,
                        "agent": agent.name,
                        "result": result,
                        "intelligence": intelligence_result,
                    }

                except Exception as exc:
                    self.database.save_execution(
                        request=request,
                        agent=agent.name,
                        status="failed",
                        result={
                            "error": str(exc),
                        },
                    )

                    self.audit_logger.log(
                        request=request,
                        action=(
                            "execution_failed"
                        ),
                        agent=agent.name,
                        allowed=False,
                        risk=risk,
                        reason=str(exc),
                        metadata={
                            "decision": decision,
                            "intelligence": intelligence,
                            "policy": policy_result,
                            "safety": safety_result,
                            "approval_id": (
                                approval_id
                            ),
                        },
                    )

                    raise

        # ---------------------------------------------------------
        # 8. AGENT RECOMMENDED BUT NOT REGISTERED
        # ---------------------------------------------------------

        self.audit_logger.log(
            request=request,
            action="agent_unavailable",
            agent=selected_agent,
            allowed=False,
            risk=risk,
            reason=(
                f"{selected_agent} agent "
                f"is not registered"
            ),
            metadata={
                "intelligence": intelligence,
            },
        )

        return {
            "status": "agent_unavailable",
            "request": request,
            "agent": selected_agent,
            "intelligence": intelligence_result,
            "message": (
                f"{selected_agent} agent "
                f"is not registered"
            ),
        }

    def close(self):
        """Close platform resources."""
        self.database.close()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.close()