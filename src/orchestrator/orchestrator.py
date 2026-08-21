from src.ai.decision_engine import DecisionEngine
from src.policy.decision_policy import DecisionPolicy
from src.safety.guardrails import SafetyGuardrails
from src.approval.approval_manager import ApprovalManager
from src.audit.audit_logger import AuditLogger
from src.persistence.database import Database


class Orchestrator:
    def __init__(self, database=None):
        """
        Main orchestration layer for the Autonomous DevOps Platform.

        A shared Database instance can be supplied so approvals,
        executions, and audit events persist across the platform.
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

    def register_agent(self, agent):
        """Register an agent with the orchestrator."""
        self.agents.append(agent)

    def run(self, context=None):
        """Run all registered agents."""
        return {
            agent.name: agent.execute(context)
            for agent in self.agents
        }

    def _requires_human_approval(self, request, safety_result):
        """
        Require human approval only for operations that can modify systems.

        Read/check/inspect operations should continue normally.
        Destructive operations are handled earlier by SafetyGuardrails.
        """

        action = safety_result.get("action", "execute")

        if action not in {"review", "escalate"}:
            return False

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

        return any(
            keyword in request_lower
            for keyword in approval_keywords
        )

    def route(self, request, context=None, approval_id=None):
        """
        Route a request through:

        DecisionEngine
        -> DecisionPolicy
        -> SafetyGuardrails
        -> Human Approval
        -> Agent Execution
        -> Persistence
        -> Audit Logging
        """

        if not request:
            raise ValueError("Request cannot be empty")

        # ---------------------------------------------------------
        # 1. AI DECISION
        # ---------------------------------------------------------
        decision = self.decision_engine.decide_agents(request)

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
                "message": "No suitable agent found",
            }

        recommended_agents = decision["recommended_agents"]

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
                "message": "No suitable agent found",
            }

        selected_agent = recommended_agents[0]

        # ---------------------------------------------------------
        # 2. DECISION POLICY
        # ---------------------------------------------------------
        policy_result = self.decision_policy.evaluate(decision)

        # ---------------------------------------------------------
        # 3. SAFETY GUARDRAILS
        # ---------------------------------------------------------
        safety_result = self.safety_guardrails.evaluate(
            request,
            policy_result=policy_result,
        )

        safety_action = safety_result.get("action", "execute")
        risk = safety_result.get("risk", "low")
        reason = safety_result.get("reason", "")

        # ---------------------------------------------------------
        # 4. HARD SAFETY BLOCK
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
            }

        # ---------------------------------------------------------
        # 5. HUMAN APPROVAL
        # ---------------------------------------------------------
        if self._requires_human_approval(
            request,
            safety_result,
        ):

            # No approval exists yet
            if approval_id is None:
                approval = self.approval_manager.create_request(
                    request=request,
                    action=safety_action,
                    agent=selected_agent,
                    risk=risk,
                    metadata={
                        "decision": decision,
                        "policy": policy_result,
                        "safety": safety_result,
                    },
                )

                self.audit_logger.log(
                    request=request,
                    action="approval_requested",
                    agent=selected_agent,
                    allowed=False,
                    risk=risk,
                    reason=reason,
                    metadata={
                        "approval_id": approval["approval_id"],
                    },
                )

                return {
                    "status": "pending_approval",
                    "request": request,
                    "agent": selected_agent,
                    "risk": risk,
                    "approval_id": approval["approval_id"],
                    "message": (
                        "Human approval required before execution"
                    ),
                }

            # Approval ID supplied
            approval = self.approval_manager.get_request(
                approval_id
            )

            if approval is None:
                return {
                    "status": "approval_not_found",
                    "request": request,
                    "agent": selected_agent,
                    "approval_id": approval_id,
                    "message": (
                        "Approval request was not found"
                    ),
                }

            if approval["status"] == "pending":
                return {
                    "status": "pending_approval",
                    "request": request,
                    "agent": selected_agent,
                    "risk": risk,
                    "approval_id": approval_id,
                    "message": "Approval is still pending",
                }

            if approval["status"] == "rejected":
                self.audit_logger.log(
                    request=request,
                    action="rejected",
                    agent=selected_agent,
                    allowed=False,
                    risk=risk,
                    reason=(
                        approval.get("reason")
                        or "Human rejected request"
                    ),
                    metadata={
                        "approval_id": approval_id,
                        "decided_by": approval.get(
                            "decided_by"
                        ),
                    },
                )

                return {
                    "status": "rejected",
                    "request": request,
                    "agent": selected_agent,
                    "approval_id": approval_id,
                    "message": (
                        "Human approval was rejected"
                    ),
                }

            if not self.approval_manager.can_execute(
                approval_id
            ):
                return {
                    "status": "pending_approval",
                    "request": request,
                    "agent": selected_agent,
                    "approval_id": approval_id,
                    "message": (
                        "Request is not approved for execution"
                    ),
                }

        # ---------------------------------------------------------
        # 6. LOCATE AND EXECUTE SELECTED AGENT
        # ---------------------------------------------------------
        for agent in self.agents:
            if agent.name.lower() == selected_agent:

                try:
                    result = agent.execute(context)

                    # Persist successful execution
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
                        reason="Request executed successfully",
                        metadata={
                            "decision": decision,
                            "policy": policy_result,
                            "safety": safety_result,
                            "approval_id": approval_id,
                        },
                    )

                    return {
                        "status": "routed",
                        "request": request,
                        "agent": agent.name,
                        "result": result,
                    }

                except Exception as exc:
                    # Persist failed execution
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
                        action="execution_failed",
                        agent=agent.name,
                        allowed=False,
                        risk=risk,
                        reason=str(exc),
                        metadata={
                            "decision": decision,
                            "policy": policy_result,
                            "safety": safety_result,
                            "approval_id": approval_id,
                        },
                    )

                    raise

        # ---------------------------------------------------------
        # 7. AGENT RECOMMENDED BUT NOT REGISTERED
        # ---------------------------------------------------------
        self.audit_logger.log(
            request=request,
            action="agent_unavailable",
            agent=selected_agent,
            allowed=False,
            risk=risk,
            reason=(
                f"{selected_agent} agent is not registered"
            ),
        )

        return {
            "status": "agent_unavailable",
            "request": request,
            "agent": selected_agent,
            "message": (
                f"{selected_agent} agent is not registered"
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