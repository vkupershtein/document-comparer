"""
CLI for document comparer
"""

from argparse import ArgumentParser
import os

import pandas as pd

from document_comparer import PDFProcessor
from document_comparer import TextMatcher

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
    parser.add_argument("--start_page_left", type=int, default=0)
    parser.add_argument("--start_header_left", type=int, default=0)
    parser.add_argument("--size_weight_left", type=float, default=1.0)
    parser.add_argument("--header_right", type=int, default=0)
    parser.add_argument("--footer_right", type=int, default=0)
    parser.add_argument("--start_page_right", type=int, default=0)
    parser.add_argument("--start_header_right", type=int, default=0)
    parser.add_argument("--size_weight_right", type=float, default=1.0)
    parser.add_argument("--ratio_threshold", type=float, default=0.5)
    parser.add_argument("--length_threshold", type=int, default=80)        

    args = parser.parse_args()

    left_paragraphs = PDFProcessor(args.left_file).extract_paragraphs(page_start = args.start_page_left, 
                                                                      top=args.header_left, 
                                                                      bottom=args.footer_left,
                                                                      top_start=args.start_header_left,
                                                                      size_weight=args.size_weight_left)
    right_paragraphs = PDFProcessor(args.right_file).extract_paragraphs(page_start = args.start_page_right, 
                                                                      top=args.header_right, 
                                                                      bottom=args.footer_right,
                                                                      top_start=args.start_header_right,
                                                                      size_weight=args.size_weight_right)
    
    comparison = TextMatcher(left_paragraphs, 
                             right_paragraphs, 
                             args.ratio_threshold, 
                             args.length_threshold).generate_comparison()

    comparison_html_df = (pd.DataFrame.from_records(comparison)
                          .fillna("")
                          .sort_values(["position", "position_secondary"])
                          .drop(columns=["text_left", "text_right", "position", "position_secondary"]))
    
    styles = [
        dict(selector="tr:hover", props=[("background-color", "#F5F5F5")]),
        dict(selector="th", props=[("font-size", "120%"), ("text-align", "left"), ("background-color", "#F2F2F2")]),
        dict(selector="td", props=[("font-size", "110%"), ("text-align", "left")]),
        dict(selector="table", props=[("border-collapse", "collapse"), ("width", "100%")]),       
        dict(selector="th,td", props=[("border", "1px solid #CCC"), ("padding", "8px")])
    ]

    styled_df = comparison_html_df.style.set_table_styles(styles)

    os.makedirs(args.output_dir, exist_ok=True)    
    styled_df.to_html(os.path.join(args.output_dir, args.output_file))


if __name__ == "__main__":
    cli()  
