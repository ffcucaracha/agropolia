from agropolia.config import Settings
from agropolia.shared.versioning import evaluate_version

def settings(): return Settings(android_latest_version="1.4.3",android_recommended_version="1.4.3",android_minimum_supported_version="1.3.0")
def test_force_update_below_minimum(): assert evaluate_version("android","1.2.9",settings())["state"]=="force_update"
def test_soft_update_below_recommended(): assert evaluate_version("android","1.3.5",settings())["state"]=="soft_update"
def test_ok_at_recommended(): assert evaluate_version("android","1.4.3",settings())["state"]=="ok"
