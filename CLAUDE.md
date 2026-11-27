# housetools — notes for Claude

A small Django app for the house: NextDNS blocking, Alexa announcements through
Voice Monkey, a Garmin watch endpoint, and the soundbar.

Infrastructure questions (the server, deploys, the home network, the soundbar
itself) belong in the `tech` repo, not here. Use the `tech` skill to reach it.

## Templates

**Never use `{# ... #}` comments.** Django only accepts them on a single line,
so a multi-line one renders as visible text on the page. One shipped to
production on 2026-11-27. Use `{% comment %} ... {% endcomment %}`.

## Deploying

Appliku, driven through its REST API with the coordinates in `.env.appliku`
(gitignored). The runbook is `tech/runbooks/appliku-deploy.md`. Push first:
Appliku builds from the pushed branch, so an unpushed commit deploys the old
code.

## The soundbar

Samsung HW-Q930D. Samsung refuses API-only OAuth apps on a personal account
(`POST /v1/apps` → 403 since the Developer Workspace closed to new integrations
on 31 August 2026), so tokens come from a WebHook SmartApp instead: SmartThings
posts to `/soundbar/smartapp/` and hands over tokens at INSTALL. What the bar
can be told to do, and by which route, is in `tech/runbooks/samsung-soundbar.md`.
