import environ

env = environ.Env(
    DEBUG=(bool, False),
)

ACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_ADAPTER = 'lebenshilfe.adapter.StaffSocialAccountAdapter'

NC_CLIENT_ID = env("NEXTCLOUD_CLIENT_ID", default=None)
NC_SECRET = env("NEXTCLOUD_SECRET", default=None)
NC_SERVER = env("NEXTCLOUD_SERVER", default=None)

if all([NC_CLIENT_ID, NC_SECRET, NC_SERVER]):
    SOCIALACCOUNT_PROVIDERS = {
        "nextcloud": {
            "APPS": [
                {
                    "client_id": NC_CLIENT_ID,
                    "secret": NC_SECRET,
                    "settings": {
                        "server": NC_SERVER,
                    }
                }
            ]
        }
    }
