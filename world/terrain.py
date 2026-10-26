"""월드에서 사용하는 지면, 발판, 가시 등의 지형 목록을 관리한다."""

class Terrain:  # 월드 지형 요소 목록을 보관
    """지형 오브젝트 목록을 보관하는 컨테이너."""
    def __init__(self):  # 지형 요소 목록을 빈 상태로 초기화
        self.platforms = []  # 생성된 발판 목록
        self.ground_segments = []  # 생성된 지면 목록
        self.spikes = []  # 생성된 가시 구간 목록
        self.ladders = []  # 생성된 사다리 목록
        self.decorations = []  # 지형 장식 목록
        self.enemies = []  # 적 목록
        self.items = []  # 획득 가능한 아이템 목록
        self.moving_platforms = []  # 왕복 이동 발판
        self.trash_mobs = []  # 근접 공격으로 처치 가능한 잡몹
        self.world_end = 0  # 생성된 월드의 마지막 좌표
