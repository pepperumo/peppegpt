# Intelligent Graph Selection

This system **automatically decides** which documents should use the expensive Knowledge Graph processing vs. simple vector search.

## How It Works

The `graph_selector.py` module analyzes each document and decides based on:

### ✅ Documents That Get Graphed

1. **High Entity Density** - Many people, organizations, dates mentioned
2. **Relationship-Heavy Content** - "worked with", "partnered with", "reports to"
3. **Complex Document Types** - Contracts, org charts, research papers
4. **Filename Indicators** - Contains "organization", "relationship", "network", etc.
5. **Sufficient Size** - At least 3 chunks (configurable)

### ❌ Documents That Skip the Graph

1. **Simple Content** - READMEs, guides, FAQs, manuals
2. **Small Documents** - Less than 3 chunks
3. **Low Complexity** - Few entities or relationships detected
4. **Simple Formats** - Plain text, markdown
5. **Certificates, Receipts, Forms** - Static/template content

## Configuration via Environment Variables

Control the selector's behavior:

```bash
# Force mode (auto, always, never)
GRAPH_MODE=auto              # Default: intelligent selection
# GRAPH_MODE=always          # Force graph for ALL documents
# GRAPH_MODE=never           # Disable graph for ALL documents

# Thresholds for automatic selection
GRAPH_MIN_CHUNKS=3           # Minimum chunks required (default: 3)
GRAPH_ENTITY_THRESHOLD=5     # Minimum entities to detect (default: 5)
GRAPH_RELATIONSHIP_THRESHOLD=0.15  # Min relationship density 0-1 (default: 0.15)
```

## Example Output

When processing documents, you'll see decisions like:

```
📊 Graph decision for 'Company_Org_Chart.pdf': ✓ USE GRAPH - High entity density (23 entities) and relationships (0.31)
✓ Added document to knowledge graph: 12 episodes created

📊 Graph decision for 'User_Manual.pdf': ✗ SKIP GRAPH - Low complexity (entities: 3, relationships: 0.05) - vector search sufficient
ⓘ Skipping knowledge graph for this document - using vector-only storage

📊 Graph decision for 'Receipt_2024.pdf': ✗ SKIP GRAPH - Filename suggests simple content: 'Receipt_2024.pdf'
ⓘ Skipping knowledge graph for this document - using vector-only storage
```

## Cost Savings

**Example scenario with 100 documents:**

### Before (All documents graphed):
- ❌ Processing time: 100 docs × 4 min = 400 minutes (~7 hours)
- ❌ API costs: 100 docs × 112 calls = 11,200 LLM calls
- ❌ Cost: ~$5-15 depending on model

### After (Intelligent selection - 20% graphed):
- ✅ Processing time: 20 docs × 4 min + 80 docs × 10s = 93 minutes
- ✅ API costs: 20 docs × 112 calls + 80 docs × 8 calls = 2,880 LLM calls
- ✅ Cost: ~$1.50-4 (70% savings!)
- ✅ Speed: 4.3x faster

## Detection Algorithms

### Entity Detection
Looks for:
- Proper nouns (capitalized names)
- Organizations (Company Inc., Corp., LLC)
- Dates (various formats)
- Email addresses
- Technical identifiers

### Relationship Detection
Scans for phrases like:
- "worked at/for/with"
- "reports to", "manager of"
- "collaborated with", "partnered with"
- "married to", "child of"
- "founder of", "owns"
- "member of", "affiliated with"

## Manual Override

### Force graph for specific document:
```python
# In your code, you can force graph usage
GRAPH_MODE=always python process_single_doc.py important_contract.pdf
```

### Disable graph temporarily:
```python
GRAPH_MODE=never python process_batch.py  # Fast vector-only processing
```

## Testing the Selector

You can test the selector logic directly:

```python
from common.graph_selector import should_use_graph_for_document

text = "Your document text here..."
chunks = ["chunk1", "chunk2", "chunk3"]
use_graph, reason = should_use_graph_for_document(
    text=text,
    chunks=chunks,
    file_title="Contract_Agreement.pdf",
    mime_type="application/pdf"
)

print(f"Use graph: {use_graph}")
print(f"Reason: {reason}")
```

## Best Practices

1. **Start with `GRAPH_MODE=auto`** - Let the system learn your document patterns
2. **Monitor decisions** - Check the logs to see which docs are graphed
3. **Adjust thresholds** - If too many/few docs are graphed, tune the environment variables
4. **Use `GRAPH_MODE=never` for testing** - Faster iterations when developing
5. **Use `GRAPH_MODE=always` for critical docs** - When building a knowledge base

## Integration

The selector is already integrated into `db_handler.py`. No code changes needed - just deploy and it works! 🎉

The system will automatically log its decisions:
```
📊 Graph decision for 'YourDoc.pdf': ✓ USE GRAPH - [reason]
```

or

```
📊 Graph decision for 'YourDoc.pdf': ✗ SKIP GRAPH - [reason]
```
