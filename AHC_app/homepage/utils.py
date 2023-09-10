from io import BytesIO
from PIL import Image

from django.core.files.uploadedfile import InMemoryUploadedFile


class ImageGenerator:
    @staticmethod
    def generate_black_image(width, height):
        image = Image.new("RGB", (width, height), (0, 0, 0))
        image_io = BytesIO()
        image.save(image_io, format="JPEG")
        return InMemoryUploadedFile(
            image_io, None, "black.jpg", "static/media/background", image_io.tell(), None
        )

    @staticmethod
    def default_profile_image():
        width, height = 100, 100
        return ImageGenerator.generate_black_image(width, height)
