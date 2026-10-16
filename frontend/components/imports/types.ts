export type PreviewData = {
  columns: string[];
  total_rows: number;
  sheets: string[] | null;
  rows: Record<string, string>[];
  suggested_mapping: Record<string, string>;
};

export type ValidationSummary = {
  total_rows: number;
  rejected_rows: number;
  duplicate_rows: number;
  valid_rows: number;
  errors: number;
  warnings: number;
  missing_by_column: Record<string, number>;
  invalid_by_column: Record<string, number>;
  outlier_quantity: number;
  outlier_revenue: number;
};

export type Issue = {
  row_num: number;
  severity: "error" | "warning";
  rule: string;
  column: string | null;
  message: string;
};

export type CleaningSummary = {
  valid_rows: number;
  rows_cleaned: number;
  duplicates_removed: number;
  rejected_rows: number;
  revenue_total: number;
  date_min: string | null;
  date_max: string | null;
};

export type Transformation = { step: string; affected_rows: number; detail: string };
export type Example = {
  row_num: number;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
};

export type JobStats = {
  validation?: ValidationSummary;
  cleaning?: (CleaningSummary & { transformations: Transformation[]; examples: Example[] }) | null;
  confirmation?: {
    confirmed_rows: number;
    revenue_total: number;
    date_min: string | null;
    date_max: string | null;
    customers: number;
    products: number;
    regions: number;
  } | null;
};

export const CANONICAL_FIELDS = [
  "order_id",
  "order_date",
  "customer_id",
  "customer_name",
  "customer_segment",
  "product_id",
  "product_name",
  "category",
  "subcategory",
  "region",
  "country",
  "sales_channel",
  "sales_rep",
  "quantity",
  "unit_price",
  "discount",
  "cost",
  "shipping_cost",
  "revenue",
  "profit",
  "payment_method",
  "order_status",
];

export const REQUIRED = ["order_id", "order_date", "quantity"];
