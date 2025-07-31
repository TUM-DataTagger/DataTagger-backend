from fdm.storages.models.storages import DefaultLocalFileSystemStorage, PrivateDSSLocalFileSystemStorage

# from storages.backends import (
#     apache_libcloud,
#     azure_storage,
#     dropbox,
#     ftp,
#     gcloud,
#     s3boto3,
#     sftpstorage
# )


__all__ = [
    "STORAGE_PROVIDER_MAP",
    "DEFAULT_STORAGE_TYPE",
]


STORAGE_PROVIDER_MAP = {
    "default_local": {
        "class": DefaultLocalFileSystemStorage,
        "name": "Default Local Storage",
        "local": True,
        "kwargs": {"path_prefix": "local"},
    },
    "private_dss": {
        "class": PrivateDSSLocalFileSystemStorage,
        "name": "Private DSS Storage",
        "local": True,
        "kwargs": {"path_prefix": "taggy/pub"},
    },
    # "libcloud": {
    #     "class": apache_libcloud.LibCloudStorage,
    #     "name": "Apache LibCloud",
    #     "local": False,
    # },
    # "azure": {
    #     "class": azure_storage.AzureStorage,
    #     "name": "Azure Blob Storage",
    #     "local": False,
    # },
    # "dropbox": {
    #     "class": dropbox.DropBoxStorage,
    #     "name": "Dropbox",
    #     "local": False,
    # },
    # "ftp": {
    #     "class": ftp.FTPStorage,
    #     "name": "FTP",
    #     "local": False,
    # },
    # "gcloud": {
    #     "class": gcloud.GoogleCloudStorage,
    #     "name": "Google Cloud Storage",
    #     "local": False,
    # },
    # "s3boto3": {
    #     "class": s3boto3.S3Boto3Storage,
    #     "name": "S3/Boto3",
    #     "local": False,
    # },
    # "do": {
    #     "class": s3boto3.S3Boto3Storage,
    #     "name": "Digital Ocean (boto3)",
    #     "local": False,
    # },
    # "sftp": {
    #     "class": sftpstorage.SFTPStorage,
    #     "name": "SFTP",
    #     "local": False,
    # },
}

DEFAULT_STORAGE_TYPE = "default_local"
