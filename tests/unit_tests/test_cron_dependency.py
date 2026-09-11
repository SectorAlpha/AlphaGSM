"""Ensure the installed cron library supplies the API AlphaGSM actually uses."""


def test_crontab_can_construct_and_serialize_reboot_job():
    from crontab import CronTab

    cron = CronTab(tab="")
    cron.new(command="alphagsm demo start").every_reboot()
    assert "@reboot alphagsm demo start" in str(cron)
