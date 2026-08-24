# Frontend Pagination Update

```typescript
interface KnowledgeBaseArticleSummary {
  id: string;
  database_id: number;
  article_number: string;
  title: string;
  description: string;
  url: string;
  instruments: string[];
  last_updated: string | null;
}

interface PaginationMetadata {
  current_page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next_page: boolean;
  has_previous_page: boolean;
  next_page: number | null;
  previous_page: number | null;
}

interface KnowledgeBaseArticlePage {
  items: KnowledgeBaseArticleSummary[];
  pagination: PaginationMetadata;
}
```