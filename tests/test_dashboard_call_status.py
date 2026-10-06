from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from django_scopes import scopes_disabled
from eventyay.base.models.auth import User

from exhibition.models import ExhibitorSettings


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("enabled", "private", "deadline_offset", "status", "message"),
    [
        (True, True, -1, "Open", "Requests can be submitted through the private link, even after the deadline."),
        (True, True, 1, "Open", "Requests can be submitted through the private link, even after the deadline."),
        (True, True, None, "Open", "Requests can be submitted through the private link, even after the deadline."),
        (True, False, -1, "Closed", "The deadline passed on"),
        (True, False, 1, "Open", "Closes on"),
        (True, False, None, "Open", "No deadline set."),
        (False, True, -1, "Disabled", "The call is not published, so nobody can submit a request."),
    ],
)
def test_dashboard_call_status(event, client, settings, enabled, private, deadline_offset, status, message):
    settings.DEBUG = True
    settings.LANGUAGES = [("en", "English")]
    settings.COMPRESS_ENABLED = False
    settings.COMPRESS_PRECOMPILERS = ()
    with scopes_disabled():
        event.plugins = "exhibition"
        event.save(update_fields=["plugins"])
        ExhibitorSettings.objects.create(
            event=event,
            call_enabled=enabled,
            call_private=private,
            call_deadline=timezone.now() + timedelta(days=deadline_offset) if deadline_offset is not None else None,
            exhibitors_access_mail_subject="",
            exhibitors_access_mail_body="",
        )
        organizer = User.objects.create_user(email="organizer@example.org", password=None)
        team = event.organizer.teams.create(name="Organizers", all_events=True, can_change_event_settings=True)
        team.members.add(organizer)
    client.force_login(organizer)

    response = client.get(
        reverse(
            "plugins:exhibition:dashboard",
            kwargs={"organizer": event.organizer.slug, "event": event.slug},
        ),
        follow=True,
    )

    assert response.status_code == 200
    html = response.content.decode()
    assert f">{status}</span>" in html
    assert message in html
    if enabled and private:
        assert ">Closed</span>" not in html
        assert "The deadline passed on" not in html
        assert "Closes on" not in html
