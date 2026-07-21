import os
import boto3
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, DigitalBox
from auth import get_current_active_user

router = APIRouter(prefix="/box", tags=["box"])

def get_s3_client():
    endpoint = os.getenv('AWS_ENDPOINT_URL', '')
    if endpoint and not endpoint.startswith('http'):
        endpoint = 'https://' + endpoint
        
    return boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

BUCKET_NAME = os.getenv("B2_BUCKET_NAME", "digitalbox-rentals-bucket")

def get_active_box(user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    box = db.query(DigitalBox).filter(DigitalBox.user_id == user.id).first()
    if not box or not box.is_active:
        raise HTTPException(status_code=403, detail="No active DigitalBox subscription found.")
    return box

@router.get("/files")
async def list_files(box: DigitalBox = Depends(get_active_box)):
    s3 = get_s3_client()
    prefix = box.storage_path
    
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    except Exception as e:
        print(f"S3 Error: {e}")
        return {"files": []}

    files = []
    if 'Contents' in response:
        for obj in response['Contents']:
            filename = obj['Key'][len(prefix):]
            if filename:
                files.append({"name": filename, "size": obj['Size']})
    
    return {"files": files}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), box: DigitalBox = Depends(get_active_box), db: Session = Depends(get_db)):
    s3 = get_s3_client()
    prefix = box.storage_path
    object_name = prefix + file.filename
    
    try:
        old_size = 0
        try:
            head = s3.head_object(Bucket=BUCKET_NAME, Key=object_name)
            old_size = head.get('ContentLength', 0)
        except Exception:
            pass
            
        s3.upload_fileobj(file.file, BUCKET_NAME, object_name)
        
        response = s3.head_object(Bucket=BUCKET_NAME, Key=object_name)
        new_size = response.get('ContentLength', 0)
    except Exception as e:
        print(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"S3/B2 Error: {str(e)}")
        
    box.current_storage_bytes += (new_size - old_size)
    box.current_storage_bytes = max(0, box.current_storage_bytes)
    db.commit()
        
    return {"filename": file.filename, "message": "File uploaded successfully"}

@router.get("/download/{filename}")
async def download_file(filename: str, box: DigitalBox = Depends(get_active_box)):
    s3 = get_s3_client()
    prefix = box.storage_path
    object_name = prefix + filename
    
    try:
        s3.head_object(Bucket=BUCKET_NAME, Key=object_name)
        s3_response = s3.get_object(Bucket=BUCKET_NAME, Key=object_name)
        return StreamingResponse(
            s3_response['Body'], 
            media_type=s3_response['ContentType'],
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=500, detail="Error downloading file")

@router.delete("/files/{filename}")
async def delete_file(filename: str, box: DigitalBox = Depends(get_active_box), db: Session = Depends(get_db)):
    s3 = get_s3_client()
    prefix = box.storage_path
    object_name = prefix + filename
    
    try:
        response = s3.head_object(Bucket=BUCKET_NAME, Key=object_name)
        file_size = response.get('ContentLength', 0)
        
        s3.delete_object(Bucket=BUCKET_NAME, Key=object_name)
        
        box.current_storage_bytes = max(0, box.current_storage_bytes - file_size)
        db.commit()
        
        return {"message": "File deleted"}
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=500, detail="Error deleting file")
