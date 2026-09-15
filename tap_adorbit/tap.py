"""Ad Orbit tap class."""

from singer_sdk import Tap
from singer_sdk.typing import IntegerType, PropertiesList, Property, StringType

from tap_adorbit.streams import (
    ActivitiesStream,
    CompaniesStream,
    CompanyAssetsStream,
    ContactsStream,
    EditorialsStream,
    OrdersStream,
    PublicationsStream,
    SubscribersStream,
    SubscriptionPlansStream,
    SubscriptionsStream,
    VendorsStream,
)


class TapAdOrbit(Tap):
    """Singer tap for Ad Orbit."""

    name = "tap-adorbit"

    config_jsonschema = PropertiesList(
        Property(
            "instance",
            StringType,
            required=True,
            description=(
                "Ad Orbit instance name (e.g. 'stage' for stage.adorbit.com). "
                "The API base URL will be https://{instance}.api.adorbit.com/."
            ),
        ),
        Property(
            "public_key",
            StringType,
            required=True,
            secret=True,
            description="Ad Orbit public API key (128 characters).",
        ),
        Property(
            "private_key",
            StringType,
            required=True,
            secret=True,
            description="Ad Orbit private API key (128 characters).",
        ),
        Property(
            "start_date",
            StringType,
            required=False,
            description=(
                "Optional start timestamp for incremental sync via X-OPT-CHANGEDSINCE "
                "(format: YYYY-MM-DD HH:MM:SS)."
            ),
        ),
        Property(
            "page_size",
            IntegerType,
            default=100,
            description="Number of records per API page (X-OPT-LIMIT header). Default: 100.",
        ),
        Property(
            "api_scheme",
            StringType,
            default="https",
            description="URL scheme for API requests (https or http). Default: https.",
        ),
    ).to_dict()

    def discover_streams(self):
        """Return a list of discovered streams."""
        return [
            CompaniesStream(self),
            ContactsStream(self),
            ActivitiesStream(self),
            OrdersStream(self),
            SubscribersStream(self),
            SubscriptionsStream(self),
            SubscriptionPlansStream(self),
            PublicationsStream(self),
            EditorialsStream(self),
            VendorsStream(self),
            CompanyAssetsStream(self),
        ]


if __name__ == "__main__":
    TapAdOrbit.cli()
