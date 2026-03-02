from abc import ABC, abstractmethod
from typing import Any, Dict
from PIL import Image

try:
    from models import VerifiedCapabilityFingerprint
except ImportError:
    from .models import VerifiedCapabilityFingerprint

class DocumentParser(ABC):
    @abstractmethod
    def parse(self, image: Image.Image) -> VerifiedCapabilityFingerprint:
        """
        Parses a document image and returns the verified capability fingerprint.
        """
        pass
