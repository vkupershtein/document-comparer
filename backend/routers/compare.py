"""
Routers for comparsion tasks
"""
import logging
import shutil
import tempfile
import os
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, Depends, HTTPException
from internal.constants import INIT_PROGRESS
import pandas as pd

from use_cases.processor_factory import detect_file_type_on_name
from use_cases import compare_documents
from internal.schemas import CompareRequest, TaskIdResponse, CompareResponse, ProgressResponse
from internal.temp_storage import TempStorage, get_storage
from internal.notifier import Notifier

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["compare"],
    responses={400: {"description": "Processing error"},
               404: {"description": "Not found"}})


@router.post("/start-task/")
def start_task(background_tasks: BackgroundTasks,
               temp_store: Annotated[TempStorage, Depends(get_storage)],
               header_left: int = Form(40), footer_left: int = Form(40),
               size_weight_left: float = Form(0.8), header_right: int = Form(40),
               footer_right: int = Form(40), size_weight_right: float = Form(0.8),
               ratio_threshold: float = Form(0.5), length_threshold: int = Form(30),
               text_column_left: str = Form(''), text_column_right: str = Form(''),
               id_column_left: str = Form(''), id_column_right: str = Form(''),
               left_file: UploadFile = File(...),
               right_file: UploadFile = File(...)) -> TaskIdResponse:
    """
    Upload files and make a comparison report
    """

    task_id = str(uuid4())
    args = CompareRequest(header_left=header_left,
                          header_right=header_right,
                          footer_left=footer_left,
                          footer_right=footer_right,
                          size_weight_left=size_weight_left,
                          size_weight_right=size_weight_right,
                          ratio_threshold=ratio_threshold,
                          length_threshold=length_threshold,
                          text_column_left=text_column_left,
                          text_column_right=text_column_right,
                          id_column_left=id_column_left,
                          id_column_right=id_column_right)

    left_path = save_upload_file_tmp(left_file)
    right_path = save_upload_file_tmp(right_file)

    background_tasks.add_task(run_comparison_task,
                              task_id,
                              left_path,
                              right_path,
                              args,
                              temp_store)
    return TaskIdResponse(task_id=task_id)


@router.get("/progress/{task_id}")
def get_task_progress(task_id: str,
                      temp_store: Annotated[TempStorage, Depends(get_storage)]) -> ProgressResponse:
    """
    Get task progress status
    """
    progress, status = temp_store.get_progress(task_id)
    if progress is None or status is None:
        raise HTTPException(
            status_code=400, detail="Task was not found")
    return ProgressResponse(progress=progress, status=status)


@router.get("/result/{task_id}")
def get_task_result(task_id: str,
                    temp_store: Annotated[TempStorage, Depends(get_storage)]) -> CompareResponse:
    """
    Get task result
    """
    dataset = temp_store.get_result(task_id)
    if dataset is None:
        raise HTTPException(
            status_code=400, detail="Data is not available or not ready yet")

    return CompareResponse(comparison=dataset)  # type: ignore


def run_comparison_task(task_id: str,
                        left_path: str,
                        right_path: str,
                        args: CompareRequest,
                        temp_store: TempStorage):
    """
    Comparison task runner
    """
    notifier = Notifier(temp_store=temp_store, task_id=task_id)
    left_file_type = detect_file_type_on_name(left_path)
    right_file_type = detect_file_type_on_name(right_path)
    try:
        notifier.notify(INIT_PROGRESS)
        comparison = compare_documents(left_path,
                                       left_file_type,
                                       right_path,
                                       right_file_type,
                                       args, notifier=notifier,
                                       mode="json")
        comparison = (pd.DataFrame.from_records(comparison)
                      .fillna("")
                      .sort_values(["position", "position_secondary"])
                      .drop(columns=["position", "position_secondary"])
                      ).to_dict("records")

        temp_store.cache_result(task_id, comparison)
        notifier.notify(99, "completed")
    except (IOError, ValueError) as ex:
        logger.warning("Handled error: %s", ex)
        temp_store.cache_progress(task_id, -1, "failed")
    except Exception as ex:  # pylint: disable=broad-exception-caught
        temp_store.cache_progress(task_id, -1, "failed")  # indicate failure
        logger.error("Unknown error occured in comparison task : %s %s",
                     type(ex), str(ex))
    finally:
        os.remove(left_path)
        os.remove(right_path)


def save_upload_file_tmp(upload_file: UploadFile) -> str:
    """
    Save uploaded file to a temporary location
    """
    filename = upload_file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is not provided")
    suffix = os.path.splitext(filename)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(upload_file.file, tmp)
        tmp_path = tmp.name
    return tmp_path
