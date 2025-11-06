# Similarity Rule

## Overview

The Similarity rule implements fuzzy text matching using various string similarity algorithms. It's perfect for grading answers that may have typos, alternative phrasings, or slight variations while still being essentially correct.

## Use Cases

- **Handling Typos**: "Photosynthesis" vs "Photosynthises"
- **Paraphrasing**: Different but equivalent expressions
- **Spelling Variations**: British vs American English
- **Minor Errors**: Accept close-enough answers
- **Flexible Grading**: When exact match is too strict

## Features

- **Multiple Algorithms**: Levenshtein distance, Jaro-Winkler, Token Sort Ratio
- **Configurable Threshold**: Set minimum similarity for full credit
- **Partial Credit**: Award proportional max_points based on similarity score
- **Multiple Reference Answers**: Compare against multiple valid answers
- **Case Sensitivity Control**: Optionally ignore case differences

## Configuration

### Required Fields

- `type`: Must be `"SIMILARITY"`
- `question_id`: The ID of the question to grade
- `reference_answers`: List of acceptable answer(s) to compare against
- `max_points`: Maximum max_points available

### Optional Fields

- `algorithm` (default: `"levenshtein"`): Similarity algorithm to use
  - `"levenshtein"`: Edit distance (character-level changes needed)
  - `"jaro_winkler"`: String similarity (good for typos and prefixes)
  - `"token_sort"`: Token-based comparison (order-independent words)
- `threshold` (default: `0.8`): Similarity score (0.0-1.0) required for full credit
- `partial_credit` (default: `true`): Award partial credit for scores below threshold
- `partial_credit_min` (default: `0.5`): Minimum percentage of max_points to award (0.0-1.0)
- `case_sensitive` (default: `false`): Whether comparison is case-sensitive
- `description`: Human-readable description of the rule

## Example

### Basic Similarity Matching

```yaml
type: SIMILARITY
question_id: q15_photosynthesis
reference_answers: ["photosynthesis"]
algorithm: levenshtein
threshold: 0.85
max_points: 5.0
partial_credit: true
case_sensitive: false
description: "Accept variations of photosynthesis"
```

### Multiple Reference Answers

```yaml
type: SIMILARITY
question_id: q16_synonym
reference_answers: 
  - "beautiful"
  - "gorgeous"
  - "stunning"
  - "lovely"
algorithm: jaro_winkler
threshold: 0.8
max_points: 3.0
description: "Accept synonyms for beautiful"
```

### Token-Based Matching

```yaml
type: SIMILARITY
question_id: q17_definition
reference_answers: ["The process by which plants convert sunlight into energy"]
algorithm: token_sort
threshold: 0.75
max_points: 10.0
partial_credit: true
partial_credit_min: 0.4
description: "Definition of photosynthesis - word order flexible"
```

## Behavior

### Algorithms

#### Levenshtein Distance
- **Measures**: Minimum character edits (insert, delete, replace) needed
- **Normalized**: 1.0 = identical, 0.0 = completely different
- **Best for**: Typos, spelling errors, character-level differences
- **Example**: "photosynthesis" vs "photosynthises" → ~0.92

#### Jaro-Winkler
- **Measures**: Character matches and transpositions
- **Bonus**: Higher scores for matching prefixes
- **Best for**: Short strings, names, typos
- **Example**: "martha" vs "marhta" → ~0.96

#### Token Sort Ratio
- **Measures**: Word-level similarity (order independent)
- **Process**: Tokenize, sort, compare
- **Best for**: Phrases, definitions, word order variations
- **Example**: "quick brown fox" vs "fox brown quick" → 1.0

### Scoring Logic

1. **Compare to References**: Calculate similarity with each reference answer
2. **Best Match**: Use highest similarity score
3. **Apply Case Handling**: Convert to lowercase if `case_sensitive=false`
4. **Award Points**:
   - If `similarity >= threshold` → full `max_points`
   - If `partial_credit=true` and `similarity < threshold`:
     - Scale max_points between 0 and `max_points`
     - Minimum: `partial_credit_min × max_points`
   - Otherwise → 0 max_points

### Partial Credit Formula

```python
if similarity >= threshold:
    max_points = max_points
elif partial_credit and similarity > 0:
    # Linear scaling from partial_credit_min to 1.0
    max_points = max_points * max(similarity, partial_credit_min)
else:
    max_points = 0
```

## Examples

### Example 1: Levenshtein with Typos

**Configuration:**
```yaml
reference_answers: ["mitochondria"]
algorithm: levenshtein
threshold: 0.85
max_points: 5.0
partial_credit: true
partial_credit_min: 0.5
```

**Grading:**
| Student Answer | Similarity | Points | Notes |
|----------------|------------|--------|-------|
| "mitochondria" | 1.00       | 5.0    | Perfect |
| "mitochondrion"| 0.92       | 5.0    | Above threshold |
| "mitocondria"  | 0.91       | 5.0    | Close enough |
| "mytochondria" | 0.84       | 4.2    | Below threshold, partial |
| "mitokondria"  | 0.83       | 4.15   | Partial credit |
| "mito"         | 0.36       | 2.5    | Min partial (0.5 × 5.0) |

### Example 2: Multiple References

**Configuration:**
```yaml
reference_answers: ["physician", "doctor", "medical doctor"]
algorithm: jaro_winkler
threshold: 0.8
max_points: 4.0
partial_credit: false
```

**Grading:**
| Student Answer | Best Match | Similarity | Points |
|----------------|------------|------------|--------|
| "doctor"       | doctor     | 1.00       | 4.0    |
| "physician"    | physician  | 1.00       | 4.0    |
| "docter"       | doctor     | 0.95       | 4.0    |
| "physican"     | physician  | 0.89       | 4.0    |
| "medic"        | medical... | 0.75       | 0.0    |

### Example 3: Token Sort for Definitions

**Configuration:**
```yaml
reference_answers: ["the powerhouse of the cell"]
algorithm: token_sort
threshold: 0.8
max_points: 8.0
partial_credit: true
```

**Grading:**
| Student Answer | Similarity | Points | Notes |
|----------------|------------|--------|-------|
| "the powerhouse of the cell" | 1.00 | 8.0 | Perfect |
| "powerhouse of the cell" | 0.93 | 8.0 | Missing article, OK |
| "the cell powerhouse" | 0.87 | 8.0 | Word order different |
| "cell's powerhouse" | 0.72 | 5.76 | Partial (0.72 × 8) |
| "mitochondria" | 0.20 | 1.6 | Low similarity |

### Example 4: Case Sensitivity

**Configuration:**
```yaml
reference_answers: ["DNA"]
algorithm: levenshtein
threshold: 0.9
max_points: 3.0
case_sensitive: true
```

**Grading:**
| Student Answer | Similarity | Points | Notes |
|----------------|------------|--------|-------|
| "DNA"          | 1.00       | 3.0    | Perfect match |
| "dna"          | 0.67       | ~2.0   | Case different |

With `case_sensitive: false`:
| Student Answer | Similarity | Points | Notes |
|----------------|------------|--------|-------|
| "DNA"          | 1.00       | 3.0    | Perfect |
| "dna"          | 1.00       | 3.0    | Case ignored |

## When to Use

✅ **Good For:**
- Answers prone to typos
- Scientific/technical terms with spelling variations
- Accepting paraphrased answers
- Short answer questions with flexibility
- Reducing frustration from minor errors

❌ **Not Ideal For:**
- When exact match is critical (use ExactMatch)
- Numeric answers (use NumericRange)
- Multiple choice (use MultipleChoice)
- Keyword detection (use Keyword)
- Complex pattern matching (use Regex)

## Algorithm Selection Guide

| Algorithm | Best For | Sensitivity To | Example Use Case |
|-----------|----------|----------------|------------------|
| Levenshtein | Typos, spelling | Character changes | "photosynthesis" with typos |
| Jaro-Winkler | Short strings, names | Transpositions, prefixes | Person names, short terms |
| Token Sort | Phrases, definitions | Word order | "Process converts X to Y" |

## Tips

1. **Set Threshold Appropriately**:
   - 0.9-1.0: Very strict, minor typos only
   - 0.8-0.9: Moderate, common misspellings
   - 0.7-0.8: Lenient, significant variations
   - < 0.7: Very lenient, may accept too much

2. **Use Multiple References**: Provide synonyms and common variations

3. **Choose Right Algorithm**:
   - Short, single words → Levenshtein or Jaro-Winkler
   - Phrases, definitions → Token Sort
   - Names, prefixes matter → Jaro-Winkler

4. **Enable Partial Credit**: Usually fairer for students

5. **Test with Real Answers**: Validate threshold with actual student responses

6. **Combine with Other Rules**: Use CompositeRule for content + similarity

## Advanced Usage

### Accepting Multiple Phrasings

```yaml
reference_answers:
  - "mitochondria are the powerhouse of the cell"
  - "the cell's powerhouse is mitochondria"
  - "mitochondria power the cell"
algorithm: token_sort
threshold: 0.7
```

### Strict Matching with Partial Credit

```yaml
threshold: 0.95          # Very high bar for full credit
partial_credit: true
partial_credit_min: 0.3  # But still give some credit for attempts
```

### No Partial Credit (Binary)

```yaml
threshold: 0.8
partial_credit: false  # Either above threshold or zero
```

## Combining with Other Rules

### Similarity + Keywords

```yaml
type: COMPOSITE
mode: AND
rules:
  - type: SIMILARITY
    reference_answers: ["cellular respiration process"]
    threshold: 0.7
    max_points: 5.0
  
  - type: KEYWORD
    required_keywords: [ATP, glucose, oxygen]
    max_points_per_required: 2.0
```

Student must have similar phrasing AND mention key terms.

## Performance Considerations

- **Token Sort**: Slower for very long texts
- **Multiple References**: Compares against each, takes best match
- **Recommend**: Keep reference answers concise when possible

## Related Rules

- **ExactMatch**: For strict matching without fuzzy logic
- **Keyword**: For checking specific terms (different from overall similarity)
- **Regex**: For pattern-based matching
- **Composite**: Combine similarity with other criteria
