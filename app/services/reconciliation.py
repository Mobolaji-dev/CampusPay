import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import orders, orderstat
from app.services.nomba import verify_transfer_status

logger = logging.getLogger(__name__)


@dataclass
class ReconIssue:
    order_id: str
    issue: str
    severity: str          
    amount: str
    vendor_id: str
    nomba_transfer_ref: str | None
    nomba_live_status: dict | None = None


@dataclass
class ReconReport:
    run_at: str
    orders_checked: int
    issues: list[ReconIssue] = field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0

    def add(self, issue: ReconIssue) -> None:
        self.issues.append(issue)
        if issue.severity == "critical":
            self.critical_count += 1
        elif issue.severity == "warning":
            self.warning_count += 1


async def run_reconciliation(db: AsyncSession, lookback_hours: int = 48) -> ReconReport:
    """
    Reconcile confirmed orders against Nomba.
    Queries orders confirmed within the last `lookback_hours` hours.

    Returns a ReconReport with every anomaly found.
    """
    report = ReconReport(
        run_at=datetime.now(timezone.utc).isoformat(),
        orders_checked=0,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)


    confirmed_result = await db.execute(
        select(orders).where(
            orders.order_status == orderstat.confirmed,
            orders.created_at >= cutoff,
        )
    )
    confirmed_orders = confirmed_result.scalars().all()
    report.orders_checked = len(confirmed_orders)

    logger.info(
        "reconciliation_started orders_checked=%d lookback_hours=%d",
        report.orders_checked,
        lookback_hours,
    )

    for order in confirmed_orders:
        
        if not order.nomba_transfer_ref:
            issue = ReconIssue(
                order_id=order.order_id,
                issue="Confirmed order has no Nomba transfer reference — vendor may not have been paid",
                severity="critical",
                amount=str(order.item_amount),
                vendor_id=order.vendor_id,
                nomba_transfer_ref=None,
            )
            report.add(issue)
            logger.error(
                "[RECON][CRITICAL] missing_transfer_ref order_id=%s vendor_id=%s amount=%s",
                order.order_id, order.vendor_id, order.item_amount,
            )
            continue  

      
        try:
            nomba_status = await verify_transfer_status(order.nomba_transfer_ref)
            nomba_code = nomba_status.get("code")
            transfer_data = nomba_status.get("data", {})
            transfer_status = (
                transfer_data.get("status")
                or transfer_data.get("transferStatus")
                or "unknown"
            )

            if nomba_code != "00":
                issue = ReconIssue(
                    order_id=order.order_id,
                    issue=f"Nomba returned non-00 code for transfer: {nomba_code} ({nomba_status.get('description', '')})",
                    severity="critical",
                    amount=str(order.item_amount),
                    vendor_id=order.vendor_id,
                    nomba_transfer_ref=order.nomba_transfer_ref,
                    nomba_live_status=nomba_status,
                )
                report.add(issue)
                logger.error(
                    "[RECON][CRITICAL] transfer_query_failed order_id=%s ref=%s nomba_code=%s",
                    order.order_id, order.nomba_transfer_ref, nomba_code,
                )

            elif transfer_status.lower() in ("failed", "reversed", "rejected"):
                issue = ReconIssue(
                    order_id=order.order_id,
                    issue=f"Nomba transfer has failed status: {transfer_status}",
                    severity="critical",
                    amount=str(order.item_amount),
                    vendor_id=order.vendor_id,
                    nomba_transfer_ref=order.nomba_transfer_ref,
                    nomba_live_status=nomba_status,
                )
                report.add(issue)
                logger.error(
                    "[RECON][CRITICAL] transfer_failed order_id=%s ref=%s status=%s",
                    order.order_id, order.nomba_transfer_ref, transfer_status,
                )

            elif transfer_status.lower() == "pending":
                issue = ReconIssue(
                    order_id=order.order_id,
                    issue=f"Transfer still pending after confirmation: {transfer_status}",
                    severity="warning",
                    amount=str(order.item_amount),
                    vendor_id=order.vendor_id,
                    nomba_transfer_ref=order.nomba_transfer_ref,
                    nomba_live_status=nomba_status,
                )
                report.add(issue)
                logger.warning(
                    "[RECON][WARNING] transfer_still_pending order_id=%s ref=%s",
                    order.order_id, order.nomba_transfer_ref,
                )

            else:
                logger.info(
                    "recon_order_ok order_id=%s ref=%s status=%s",
                    order.order_id, order.nomba_transfer_ref, transfer_status,
                )

        except Exception as exc:
            logger.error(
                "[RECON] nomba_lookup_exception order_id=%s ref=%s error=%s",
                order.order_id, order.nomba_transfer_ref, exc,
            )
            report.add(ReconIssue(
                order_id=order.order_id,
                issue=f"Could not verify transfer with Nomba: {exc}",
                severity="warning",
                amount=str(order.item_amount),
                vendor_id=order.vendor_id,
                nomba_transfer_ref=order.nomba_transfer_ref,
            ))

    logger.info(
        "reconciliation_complete orders=%d critical=%d warnings=%d",
        report.orders_checked,
        report.critical_count,
        report.warning_count,
    )
    return report
