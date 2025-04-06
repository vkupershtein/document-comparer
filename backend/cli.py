"""
CLI for document comparer
"""

from argparse import ArgumentParser
import logging
import os

import pandas as pd

from schemas import CompareRequest
from use_cases import compare_documents

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

pdf_logger = logging.getLogger("pdfminer")
pdf_logger.setLevel(logging.ERROR)

def cli():
    """
    Command line interface
    """

    parser = ArgumentParser(prog="Document Comparer", 
                            description="Makes comparison report between two documents")
    
    parser.add_argument("left_file")
    parser.add_argument("right_file")
    parser.add_argument("--output_dir", default="./reports")
    parser.add_argument("--output_file", default="report.html")
    parser.add_argument("--header_left", type=int, default=0)
    parser.add_argument("--footer_left", type=int, default=0)
    parser.add_argument("--size_weight_left", type=float, default=0.8)
    parser.add_argument("--header_right", type=int, default=0)
    parser.add_argument("--footer_right", type=int, default=0)
    parser.add_argument("--size_weight_right", type=float, default=0.8)
    parser.add_argument("--ratio_threshold", type=float, default=0.5)
    parser.add_argument("--length_threshold", type=int, default=80)        

    args = parser.parse_args()

    comparison = compare_documents(args.left_file, args.right_file, CompareRequest(size_weight_left=args.size_weight_left,
                                               size_weight_right=args.size_weight_right,
                                               header_left=args.header_left,
                                               header_right=args.header_right,
                                               footer_left=args.footer_left,
                                               footer_right=args.footer_right,
                                               ratio_threshold=args.ratio_threshold, 
                                               length_threshold=args.length_threshold), 
                                               "html")

    logger.info("Produce HTML report")    
    
    comparison_html_df = (pd.DataFrame.from_records(comparison)
                          .fillna("")
                          .sort_values(["position", "position_secondary"])
                          .drop(columns=["position", "position_secondary", "text_left", "text_right"])
                          .astype(str))   
    
    styles = [
        dict(selector="tr:hover", props=[("background-color", "#F5F5F5")]),
        dict(selector="th", props=[("font-size", "120%"), ("text-align", "left"), ("background-color", "#F2F2F2")]),
        dict(selector="td", props=[("font-size", "110%"), ("text-align", "left")]),
        dict(selector="table", props=[("border-collapse", "collapse"), ("width", "100%")]),       
        dict(selector="th,td", props=[("border", "1px solid #CCC"), ("padding", "8px")])
    ]

    styled_df = comparison_html_df.style.set_table_styles(styles) # type: ignore

    os.makedirs(args.output_dir, exist_ok=True)    
    styled_df.to_html(os.path.join(args.output_dir, args.output_file))


if __name__ == "__main__":
    cli()  
