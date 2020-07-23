"""Lambda function to post-process business level fields from raw Textract result in S3

...with just some simple rules and an Amazon Comprehend call, for our receipt digitization example.
"""

# Python Built-Ins:
import json

# External Dependencies:
import boto3

# Local Dependencies:
from trp import Document

comprehend = boto3.client("comprehend")
s3 = boto3.resource("s3")


class MalformedRequest(ValueError):
    pass


def handler(event, context):
    try:
        srcbucket = event["Bucket"]
        srckey = event["Key"]
    except KeyError as ke:
        raise MalformedRequest(f"Missing field {ke}, please check your input payload")

    # Load and parse Textract result from S3
    textract_result = json.load(s3.Object(srcbucket, srckey).get()["Body"])
    doc = Document(textract_result)

    # Define post processing variables
    amount_form_keys = ["total", "amount"]
    date_form_keys = ["date"]
    text = ""
    
    # Since we're just taking the first line as the vendor name, there'll be exactly one candidate:
    vendor_name_result = { "Confidence": 0, "Value": "" }
    vendor_name_candidates = [vendor_name_result]

    # For the other fields, we'll search for multiple options:
    date_candidates = []
    total_amount_candidates = []

    # Receipts don't usually list out a key-value pair like "Vendor: XYZ", the business name is just the
    # first thing on the receipt! So we'll make that our assumption to extract vendor:
    for item in textract_result["Blocks"]:
        if item["BlockType"] == "LINE":
            if vendor_name_result["Value"] == "":
                vendor_name_result["Value"] = item["Text"]
                # Setting the vendor name confidence = raw OCR confidence is a bit lazy and optimistic,
                # because we're not applying any reduction to reflect the fact that taking first line of
                # text = vendor name is an *assumption*... But it'll do for our sample:
                vendor_name_result["Confidence"] = item["Confidence"]
            else:
                # While we're looping through blocks anyway, we'll also collect all the text from the receipt
                # into a single string to search with Comprehend later:
                text += item["Text"] + " "

    # For amount and date fields, we'll try searching the key-value pairs first:
    # TODO: Refactor this loop for efficiency
    for page in doc.pages:
        for key in amount_form_keys:
            fields = page.form.searchFieldsByKey(key)
            for field in fields:
                # TODO: This should re-use amount_form_keys
                if (
                    ("total" in field.key.text.lower() or "amount" in field.key.text.lower())
                    and field.value is not None
                ):
                    try:
                        # If it's the total, the value should be parseable as a number!
                        # TODO: Allow for other leading currency symbols and 3-letter-acronyms
                        a = float(field.value.text.lstrip("$"))
                        total_amount_candidates.append({
                            # Again because we're post-processing, our output "Confidence" scores should be
                            # driven by the Textract outputs but adjusted to reflect our business
                            # understanding... We'll take another pretty simple choice here:
                            "Confidence": min(field.key.confidence, field.value.confidence),
                            "Value": field.value.text,
                        })
                    except Exception as e:
                        print("Cannot proceed String to Number {}".format(field.value.text))

        for key in date_form_keys:
            fields = page.form.searchFieldsByKey(key)
            for field in fields:
                if "date" in field.key.text.lower() and field.value is not None:
                    date_candidates.append({
                        "Confidence": min(field.key.confidence, field.value.confidence),
                        "Value": field.value.text
                    })

    # If we couldn't find any date-looking fields in the key-value pairs (likely for verbose invoice-style
    # documents, but not for shorrt receipts), then we'll use Amazon Comprehend to just detect date entities:
    if not len(date_candidates) > 0:
        comprehend_entities = comprehend.detect_entities(Text=text, LanguageCode="en")["Entities"]
        for entity in comprehend_entities:
            if entity.get("Type") == "DATE":
                value_str = entity.get("Text").strip("\t\n\r")
                # A little bit of validation that it looks date-like:
                if "/" in value_str or ":" in value_str or "-" in value_str:
                    date_candidates.append({
                        # Comprehend scores confidence 0-1 while Textract does 0-100: Doesn't matter which we
                        # standardize on as long as we choose one! Again, could improve this confidence score
                        # by factoring in things like how confident the Textract OCR was on that span of text
                        "Confidence": entity.get("Score", 0) * 100,
                        "Value": value_str
                    })

    # Sort our candidates by descending confidence and take the highest confidence candidate for each field:
    date_candidates = sorted(date_candidates, key=lambda c: c["Confidence"], reverse=True)
    total_amount_candidates = sorted(total_amount_candidates, key=lambda c: c["Confidence"], reverse=True)
    date_result = date_candidates[0] if len(date_candidates) else None
    total_amount_result = total_amount_candidates[0] if len(total_amount_candidates) else None

    result = {
        "Date": {
            "Confidence": date_result["Confidence"] if date_result else 0,
            "Value": date_result["Value"] if date_result else "",
        },
        "Total": {
            "Confidence": total_amount_result["Confidence"] if total_amount_result else 0,
            "Value": total_amount_result["Value"] if total_amount_result else "",
        },
        "Vendor": {
            "Confidence": vendor_name_result["Confidence"] if vendor_name_result else 0,
            "Value": vendor_name_result["Value"] if vendor_name_result else "",
        },
    }

    # How do we measure composite result "Confidence" for many fields driven by different logics? We'll just
    # take the minimum, since a human review should be triggered by the weakest field.
    result["Confidence"] = min(map(lambda f: result[f]["Confidence"], result.keys()))
    if len(date_candidates) > 1:
        result["Date"]["Alternatives"] = date_candidates[1:]
    if len(total_amount_candidates) > 1:
        result["Total"]["Alternatives"] = total_amount_candidates[1:]
    if len(vendor_name_candidates) > 1:
        result["Vendor"]["Alternatives"] = vendor_name_candidates[1:]

    return result
