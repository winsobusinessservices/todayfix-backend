from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import AccountDeletionRequest
from accounts.services.account_deletion import (
    AccountDeletionService,
)


class Command(BaseCommand):

    help = "Processes scheduled account deletion requests."

    def handle(self, *args, **options):
        now = timezone.now()

        requests = AccountDeletionRequest.objects.filter(
            status__in=[
                AccountDeletionRequest.STATUS_PENDING,
                AccountDeletionRequest.STATUS_ON_HOLD,
            ]
        ).select_related("user")

        processed = 0
        cancelled = 0
        held = 0

        for deletion_request in requests:

            user = deletion_request.user

            if deletion_request.status == (
                AccountDeletionRequest.STATUS_PENDING
            ):

                if (
                    now < deletion_request.scheduled_deletion_at
                ):
                    continue

                if AccountDeletionService.are_conditions_clear(
                    user
                ):
                    if AccountDeletionService.finalize_deletion(
                        deletion_request
                    ):
                        processed += 1

                else:
                    AccountDeletionService.put_on_hold(
                        deletion_request
                    )

                    held += 1

                continue

            # -------------------------------------------------
            # ON HOLD
            # -------------------------------------------------

            if deletion_request.status == (
                AccountDeletionRequest.STATUS_ON_HOLD
            ):

                if AccountDeletionService.are_conditions_clear(
                    user
                ):

                    AccountDeletionService.mark_conditions_cleared(
                        deletion_request
                    )

                    continue

                if (
                    deletion_request.extension_deadline
                    and now >= deletion_request.extension_deadline
                ):

                    deletion_request.status = (
                        AccountDeletionRequest.STATUS_CANCELLED
                    )
                    deletion_request.cancelled_at = now
                    deletion_request.cancellation_reason = (
                        "Required bookings/payments were not "
                        "completed within the allowed extension period."
                    )

                    deletion_request.save(
                        update_fields=[
                            "status",
                            "cancelled_at",
                            "cancellation_reason",
                        ]
                    )

                    cancelled += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Account deletion processing completed. "
                f"Deleted: {processed}, "
                f"Cancelled: {cancelled}, "
                f"On hold: {held}"
            )
        )