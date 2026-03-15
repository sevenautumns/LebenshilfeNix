from django.contrib.auth.models import Group
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class StaffSocialAccountAdapter(DefaultSocialAccountAdapter):
    def _sync_user_data(self, user, sociallogin):
        nextcloud_groups = sociallogin.account.extra_data.get('groups', [])
        user.is_staff = True
        user.is_superuser = 'admin' in nextcloud_groups
        
        if user.pk:
            user.save()
            django_groups = []
            for group_name in nextcloud_groups:
                if group_name == 'admin':
                    continue
                group, _ = Group.objects.get_or_create(name=group_name)
                django_groups.append(group)

            user.groups.set(django_groups)

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            self._sync_user_data(sociallogin.user, sociallogin)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        self._sync_user_data(user, sociallogin)
        return user
