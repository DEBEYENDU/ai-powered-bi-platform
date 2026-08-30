from .extract import ExtractStage
from .profile import ProfileStage
from .clean import CleanStage
from .transform import TransformStage

def default_stages() -> list:
    return [ExtractStage(), ProfileStage(), CleanStage(), TransformStage()]