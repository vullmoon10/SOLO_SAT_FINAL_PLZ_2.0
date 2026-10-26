"""피해량을 적용하고 플레이어 체력의 유효 범위를 보장한다."""

def apply_damage(current_hp, damage, no_damage=False):  # 피해량을 반영하고 체력을 0 이상으로 제한
    """피해를 적용하고 체력이 0 미만으로 내려가지 않게 한다."""
    # 무피해 모드에서는 체력을 그대로 두고 유효 범위로 제한한다.
    if no_damage:  # 무피해 설정이면 체력을 유지
        return max(0, current_hp)
    return max(0, current_hp - max(0, damage))
