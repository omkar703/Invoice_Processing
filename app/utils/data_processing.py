import pandas as pd
from typing import List

from app.core.logging import logger


def merge_dataframes_intelligently(standardized_dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Merge standardized DataFrames, handling different column sets intelligently.
    
    Args:
        standardized_dfs: List of DataFrames with standardized column names
        
    Returns:
        Single merged DataFrame
    """
    if not standardized_dfs:
        logger.warning("No DataFrames provided for merging")
        return pd.DataFrame()
    
    if len(standardized_dfs) == 1:
        logger.info("Single DataFrame provided, returning as-is")
        return standardized_dfs[0]
    
    # Collect all unique column names
    all_columns = set()
    for df in standardized_dfs:
        all_columns.update(df.columns.tolist())
    
    logger.info(f"Merging {len(standardized_dfs)} DataFrames with columns: {list(all_columns)}")
    
    # Align all DataFrames to have the same columns
    aligned_dfs = []
    for i, df in enumerate(standardized_dfs):
        df_copy = df.copy()
        
        # Add missing columns with None values
        for col in all_columns:
            if col not in df_copy.columns:
                df_copy[col] = None
        
        # Reorder columns consistently
        df_copy = df_copy[sorted(all_columns)]
        aligned_dfs.append(df_copy)
        
        logger.debug(f"Aligned DataFrame {i+1}: {len(df_copy)} rows, {len(df_copy.columns)} columns")
    
    # Merge all DataFrames
    merged_df = pd.concat(aligned_dfs, ignore_index=True)
    
    logger.info(f"Successfully merged into single DataFrame: {len(merged_df)} rows, {len(merged_df.columns)} columns")
    return merged_df


def validate_dataframe(df: pd.DataFrame, required_columns: List[str] = None) -> bool:
    """
    Validate DataFrame structure and content.
    
    Args:
        df: DataFrame to validate
        required_columns: Optional list of required column names
        
    Returns:
        True if valid, False otherwise
    """
    if df is None or df.empty:
        logger.warning("DataFrame is None or empty")
        return False
    
    if required_columns:
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"DataFrame missing required columns: {missing_columns}")
            return False
    
    logger.debug(f"DataFrame validation passed: {len(df)} rows, {len(df.columns)} columns")
    return True


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean DataFrame by removing empty rows and standardizing data types.
    
    Args:
        df: DataFrame to clean
        
    Returns:
        Cleaned DataFrame
    """
    original_rows = len(df)
    
    # Remove completely empty rows
    df = df.dropna(how='all')
    
    # Remove rows where all important columns are None/empty
    important_columns = ['description', 'quantity', 'unit_price', 'total_price']
    available_columns = [col for col in important_columns if col in df.columns]
    
    if available_columns:
        df = df.dropna(subset=available_columns, how='all')
    
    # Clean numeric columns
    numeric_columns = ['quantity', 'unit_price', 'total_price', 'tax_amount', 'total_amount', 'subtotal']
    for col in numeric_columns:
        if col in df.columns:
            # Convert to numeric, replacing non-numeric values with NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Clean string columns
    string_columns = ['description', 'item_code', 'invoice_number', 'vendor_name', 'source_file', 'address', 'date_and_time', 'due_date', 'company_name']
    for col in string_columns:
        if col in df.columns:
            # Strip whitespace and replace empty strings with None
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace('', None)
            df[col] = df[col].replace('nan', None)
    
    cleaned_rows = len(df)
    if original_rows != cleaned_rows:
        logger.info(f"Cleaned DataFrame: {original_rows} -> {cleaned_rows} rows")
    
    return df
