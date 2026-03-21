# System-Wide Install

This install path is for a shared machine where AlphaGSM is installed once and used by multiple people.

## Layout

The system-wide install is designed around these paths:

- overall config: `/etc/alphagsm.conf`
- shared download user home: `/home/alphagsm`
- code: `/usr/local/lib/alphagsm`
- shared command: `/usr/local/bin/alphagsm`
- root git helper: `/usr/local/sbin/gitalphagsm`
- sudoers file: `/etc/sudoers.d/gameservers`

The shared download user can own common download data so that normal users are not all downloading and storing the same artifacts at the same time.

## Run It

Run as root:

```bash
sudo bash ./scripts/install-system-wide.sh
```

## Shared Download User

The installer creates or uses the `alphagsm` system user and prepares:

- `/home/alphagsm/gitlive`
- `/home/alphagsm/downloads`

## Sudoers Entry

The installer writes:

```text
%alphagsm       ALL = (alphagsm) NOPASSWD:/usr/local/lib/alphagsm/alphagsm-downloads
```

That allows the right group to run the shared downloader helper as the `alphagsm` user without a password prompt.

## Notes

- This is the better fit for a shared host.
- The root helper `gitalphagsm` is installed to `/usr/local/sbin/gitalphagsm`.
- The `alphagsm` command is exposed through `/usr/local/bin/alphagsm`.
