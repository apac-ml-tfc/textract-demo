# OCR Post-Processing with AWS Lambda and Amazon Comprehend

Post-processing is the important link that connects our raw Textract outputs (text, tables, and verbatim key-value pairs) to our business-level targets (receipt vendor, date, and total amount).

## Solution Architecture

Post-processing can be as simple (e.g. basic extraction of Textract key-value pairs) or as complex (e.g. deep learning models to transform the result as a whole) as you need.

In this example, we use a **mainly rule-based algorithm** (with a little help from [Amazon Comprehend](https://aws.amazon.com/comprehend/)) - implemented in an AWS Lambda function:

**For Vendor:**

- The vendor name is typically the heading of the receipt, and doesn't have explicit labelling e.g. *"Vendor: Amazon"*.
- Therefore we hard-code an assumption that the **first line** of the receipt text is the vendor name.
- An alternative could be to use NLP entity detection techniques (e.g. with [Amazon SageMaker](https://aws.amazon.com/sagemaker/)) to pick out text which appears to be a company name.

**For Total:**

- The total value is typically explicitly labelled e.g. "TOTAL: 4.86", although the exact text of the label may vary (e.g. 'Total Payable', etc).
- Therefore we **search for appropriately-named key-value pairs** in the Textract output, and check that the associated value is numeric.
- Note that some additional processing to allow for currency symbols in 'numerics' would be a good idea here!

**For Date:**

- The transaction date is sometimes labelled explicitly, but often not.
- Therefore we **search for appropriately-named key-value pairs** in the Textract output, and if none are found we call [Amazon Comprehend Detect Entities](https://docs.aws.amazon.com/comprehend/latest/dg/how-entities.html) to find any `DATE` type entities in the receipt text.

|`NOTE` | Even though we're processing the output with rules, we should still output some *confidence scores* |
|-|-|

This sample reports both per-field and overall confidence scores, derived from the input Textract and Comprehend confidence scores and some heuristics for the rules we applied.

The more closely we can make our overall confidence score correlate to the **probability the result is correct**, the more useful it will be and the better results we can get from a combination of automatic processing and human review!
