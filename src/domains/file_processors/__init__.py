import hashlib
import os
import io
from pydantic import List, Optional
import boto3
from fastapi import UploadFile

from