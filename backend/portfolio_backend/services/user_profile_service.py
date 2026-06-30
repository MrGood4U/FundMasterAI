from daos.user_profile_dao import UserProfileDao


class UserProfileService:
    """单用户系统的用户信息 Service — 始终操作 id=1 这一条记录。"""

    def __init__(self):
        self.dao = UserProfileDao()

    def get_profile(self) -> dict:
        """获取用户个人信息。"""
        row = self.dao.get()
        if row is None:
            return {}
        return dict(row)

    def update_phone(self, phone: str) -> bool:
        """更新手机号，并重置验证状态。"""
        if not phone or not phone.strip():
            return False
        phone = phone.strip()
        if not phone.isdigit() or len(phone) < 7:
            return False
        return self.dao.update_phone(phone)

    def update_email(self, email: str) -> bool:
        """更新邮箱，并重置验证状态。"""
        if not email or not email.strip():
            return False
        email = email.strip()
        if "@" not in email or "." not in email.split("@")[-1]:
            return False
        return self.dao.update_email(email)

    def update(self, phone: str = None, email: str = None) -> bool:
        """更新手机号和/或邮箱。"""
        if phone is not None and phone.strip():
            phone = phone.strip()
            if not phone.isdigit() or len(phone) < 7:
                return False
        else:
            phone = None

        if email is not None and email.strip():
            email = email.strip()
            if "@" not in email or "." not in email.split("@")[-1]:
                return False
        else:
            email = None

        if phone is None and email is None:
            return False

        self.dao.upsert(phone=phone, email=email)
        return True
