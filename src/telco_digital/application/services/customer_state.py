from __future__ import annotations

from telco_digital.application.commands.commands import GetCustomerStateQuery
from telco_digital.application.queries.dtos import ObservedCustomerState
from telco_digital.application.services.common import primary_account, require_customer
from telco_digital.application.unit_of_work.protocol import UnitOfWork
from telco_digital.domain.rules.travel import location_at
from telco_digital.domain.value_objects import display_country


async def get_customer_state(
    uow: UnitOfWork,
    query: GetCustomerStateQuery,
) -> ObservedCustomerState:
    """Observed facts at as_of. Uses only occurred_at <= as_of."""
    async with uow:
        customer = await require_customer(uow, query.customer_ref)
        as_of = query.as_of
        account = await primary_account(uow, customer.id)
        balance = await uow.ledgers.balance_at(account.id, as_of)

        travels = list(await uow.travels.list_as_of(customer.id, as_of))
        loc = location_at(home_country=customer.home_country, travels=travels, as_of=as_of)
        trip_duration_known = True
        active_travel_id = None
        if loc.travel is not None:
            active_travel_id = loc.travel.id
            # ended_at after as_of is future leakage — at as_of the trip was still open.
            trip_duration_known = loc.travel.ended_at is not None and loc.travel.ended_at <= as_of

        subscription = await uow.subscriptions.active_at(customer.id, as_of)
        plan_code = None
        if subscription is not None:
            plan = await uow.plans.get_by_id(subscription.plan_id)
            if plan is not None:
                plan_code = plan.plan_code

        link = await uow.customer_devices.active_at(customer.id, as_of)
        device_ref = None
        if link is not None:
            device = await uow.devices.get_by_id(link.device_id)
            if device is not None:
                device_ref = device.device_ref

        complaints = await uow.service_interactions.open_count(customer.id, as_of)
        warnings = await uow.warnings.list_by_customer(customer.id, as_of=as_of)

        return ObservedCustomerState(
            customer_id=customer.id,
            customer_ref=customer.customer_ref,
            as_of=as_of,
            home_country=customer.home_country,
            home_country_name=display_country(customer.home_country),
            country=loc.country_code,
            country_name=display_country(loc.country_code),
            country_source=loc.source,
            current_plan_code=plan_code,
            balance_amount=balance,
            currency=account.currency,
            loyalty_points=0,
            device_ref=device_ref,
            active_complaints=complaints,
            active_travel_id=active_travel_id,
            trip_duration_known=trip_duration_known,
            warnings=[w.warning_type.value for w in warnings],
        )
