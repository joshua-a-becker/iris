# Mail MCP Server for Claude Code

## What this is
A local MCP server that lets Claude send and receive email via the Postfix mail server on `mail.example.com` ([SERVER_IP]).

## Tools available after restart
- **`send_email(to, subject, body, from_addr?)`** — Send email. Default sender: `postmaster@[YOUR_DOMAIN]`
- **`check_email(limit?)`** — Read recent messages from the mailbox (default: last 10)
- **`check_mail_log(lines?)`** — View Postfix delivery logs

## Setup summary
- **MTA**: Postfix on Ubuntu 24.04
- **DKIM**: OpenDKIM signing with `mail._domainkey.example.com`
- **SPF**: `v=spf1 ip4:[SERVER_IP] ~all`
- **DNS**: Cloudflare (nameservers: porter/savanna.ns.cloudflare.com)
- **Mailbox**: `/var/mail/root` (mbox format, `postmaster` aliased to `root`)

## Known issues
- **Gmail rejects mail** — negative DNS cache from before SPF/DKIM were added. Retry after ~30 min or wait for cache to expire.
- **PTR record missing** — rename the DigitalOcean droplet to `mail.example.com` to fix reverse DNS. This will reduce spam flagging.
- **No DMARC record** — optionally add TXT `_dmarc` → `v=DMARC1; p=none; rua=mailto:postmaster@[YOUR_DOMAIN]` in Cloudflare.

## Config location
`~/.claude/settings.json` → `mcpServers.email` points to `/home/claude/mail-mcp/server.py`

## To restart
Just exit and relaunch Claude Code. The MCP server starts automatically.

## Next steps
After restarting Claude Code, do the following:

1. **Test the email tools work** — Use `check_email` to read the mailbox and confirm the MCP server is connected.
2. **Retry sending to Gmail** — Use `send_email` to send a test to `${OWNER_EMAIL}`. The DNS negative cache from earlier should have expired by now, so SPF and DKIM should pass. Check delivery with `check_mail_log`.
3. **Send a fresh test to UCL** — Use `send_email` to send to `${OWNER_UCL_EMAIL}` and confirm it no longer gets flagged as spam.
4. **Fix PTR record** — In the DigitalOcean control panel, rename this droplet to `mail.example.com`. This sets the reverse DNS (PTR) record, which many mail servers check. Without it, some servers flag mail as spam.
5. **Verify PTR propagated** — Run `dig -x [SERVER_IP] @8.8.8.8 +short` and confirm it returns `mail.example.com`.
6. **Add DMARC (optional)** — In Cloudflare, add a TXT record: name `_dmarc`, content `v=DMARC1; p=none; rua=mailto:postmaster@[YOUR_DOMAIN]`.
