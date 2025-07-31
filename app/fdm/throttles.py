from rest_framework.throttling import UserRateThrottle


class UltraHighRateThrottle(UserRateThrottle):
    scope = "ultrahigh"


class HighRateThrottle(UserRateThrottle):
    scope = "high"


class StandardRateThrottle(UserRateThrottle):
    scope = "standard"


class LowRateThrottle(UserRateThrottle):
    scope = "low"
