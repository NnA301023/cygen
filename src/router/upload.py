from pathlib import Path
import uuid
import traceback
from typing import List
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
import aiofiles
from loguru import logger

from ..settings import get_settings
from ..utils.background_tasks import BackgroundTaskManager

settings = get_settings()
router = APIRouter()
task_manager = BackgroundTaskManager()

# Ensure upload directory exists
upload_dir = Path(settings.PDF_UPLOAD_DIR)
upload_dir.mkdir(exist_ok=True)

class TaskResponse(BaseModel):
    """Response model for upload tasks."""
    task_id: str
    file_name: str
    status: str
    created_at: datetime

@router.post("/upload", response_model=TaskResponse)
async def upload_single_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a single PDF file for processing.
    
    Args:
        file: PDF file to upload
        background_tasks: FastAPI background tasks
        
    Returns:
        TaskResponse: Task information
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed"
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{file.filename}"
        file_path = upload_dir / safe_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create task
        task_id = str(uuid.uuid4())
        task_data = {
            "task_id": task_id,
            "file_name": file.filename,
            "file_path": str(file_path),
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        
        # Store task in MongoDB
        await task_manager.mongo_client[settings.MONGODB_DB_NAME].tasks.insert_one(task_data)
        
        # Start processing in background
        background_tasks.add_task(
            task_manager.process_pdf_task,
            str(file_path),
            task_id
        )
        
        logger.info(f"Started processing task {task_id} for file {file.filename}")
        return TaskResponse(**task_data)
        
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error processing upload"
        )

@router.post("/upload/batch", response_model=List[TaskResponse])
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload multiple PDF files for processing.
    
    Args:
        files: List of PDF files to upload
        background_tasks: FastAPI background tasks
        
    Returns:
        List[TaskResponse]: List of task information
    """
    responses = []
    for file in files:
        try:
            response = await upload_single_file(file, background_tasks)
            responses.append(response)
        except HTTPException as e:
            logger.warning(f"Skipping file {file.filename}: {str(e)}")
            continue
    
    if not responses:
        traceback.print_exc()
        raise HTTPException(
            status_code=400,
            detail="No valid files were uploaded"
        )
    
    return responses

@router.get("/task/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a processing task.
    
    Args:
        task_id: Task identifier
        
    Returns:
        TaskResponse: Task information
    """
    task = await task_manager.mongo_client[settings.MONGODB_DB_NAME].tasks.find_one(
        {"task_id": task_id}
    )
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    
    return TaskResponse(**task) 