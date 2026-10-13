import io
import uuid
import logging
from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.conf import settings
from .models import ItemReport, ReportImage, ImageModerationStatus

logger = logging.getLogger(__name__)

ALLOWED_FORMATS = {
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'WEBP': 'image/webp',
}

class ImageUploadService:
    @staticmethod
    def process_and_sanitize_image(uploaded_file):
        """
        Validates image signature, enforces size limit, and strips all EXIF metadata.
        Returns (ContentFile, content_type, size_bytes).
        """
        max_bytes = getattr(settings, 'UPLOAD_MAX_BYTES', 5242880)
        if uploaded_file.size > max_bytes:
            raise ValidationError(f"File size exceeds the 5MB limit ({max_bytes} bytes).")

        try:
            image = Image.open(uploaded_file)
            image.verify()
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
        except Exception as e:
            logger.warning(f"Image validation failed: {e}")
            raise ValidationError("The uploaded file is not a valid or readable image.")

        img_format = image.format
        if img_format not in ALLOWED_FORMATS:
            raise ValidationError(f"Unsupported image format: {img_format}. Allowed formats: JPEG, PNG, WEBP.")

        # Handle color modes
        save_format = img_format
        if img_format == 'JPEG' and image.mode in ('RGBA', 'P', 'LA'):
            image = image.convert('RGB')

        # Re-save to clean BytesIO buffer without EXIF metadata
        output = io.BytesIO()
        image.save(output, format=save_format)
        output.seek(0)
        clean_bytes = output.getvalue()

        extension = 'jpg' if save_format == 'JPEG' else save_format.lower()
        clean_filename = f"{uuid.uuid4().hex}.{extension}"
        content_type = ALLOWED_FORMATS[img_format]

        content_file = ContentFile(clean_bytes, name=clean_filename)
        return content_file, content_type, len(clean_bytes)

    @classmethod
    def attach_image_to_report(cls, report: ItemReport, uploaded_file, user=None) -> ReportImage:
        """
        Processes and stores an image associated with an ItemReport.
        """
        content_file, content_type, size_bytes = cls.process_and_sanitize_image(uploaded_file)
        
        report_image = ReportImage.objects.create(
            report=report,
            image_file=content_file,
            content_type=content_type,
            size_bytes=size_bytes,
            uploaded_by=user,
            moderation_status=ImageModerationStatus.APPROVED
        )
        return report_image
