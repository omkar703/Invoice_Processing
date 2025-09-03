# S3 Service has been deprecated - application now uses direct file uploads
# This entire file is now deprecated. The application has been modified
# to accept direct file uploads instead of using S3 storage.

# Placeholder class to prevent import errors
class S3Service:
    """Deprecated S3 Service - now using direct file uploads"""
    
    def __init__(self):
        # Deprecated - no longer initializing S3 client
        pass
    
    def download_file(self, file_key: str):
        raise NotImplementedError("S3 service has been deprecated")
    
    def check_file_exists(self, file_key: str):
        raise NotImplementedError("S3 service has been deprecated")
    
    def list_files(self, prefix: str = "", max_keys: int = 1000):
        raise NotImplementedError("S3 service has been deprecated")
    
    def get_file_info(self, file_key: str):
        raise NotImplementedError("S3 service has been deprecated")


# Global S3 service instance - DEPRECATED but needed for imports
s3_service = S3Service()
