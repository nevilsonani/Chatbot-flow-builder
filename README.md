# Lead Generation Tool

A powerful lead generation tool that helps you find and enrich company information using various APIs including Apollo.io, Hunter.io, and OpenAI.

## Features

- Search for companies based on size, industry, and location
- Enrich company data with additional information
- Find and verify email addresses
- Generate personalized outreach messages using AI
- Export leads to CSV format
- Google Sheets integration for data storage

## Prerequisites

- Python 3.7+
- API keys for the following services:
  - Apollo.io
  - Hunter.io
  - OpenAI
  - Google Sheets (optional)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/nevilsonani/Chatbot-flow-builder.git
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```


## Usage

### Basic Usage

```bash
python leadgen.py
```

### Command Line Arguments

- `--size`: Company size range (e.g., "50-200")
- `--industry`: Industry to target (e.g., "software", "hardware")
- `--location`: Location filter (e.g., "New York")
- `--output`: Output file name (default: "leads_output.csv")
- `--limit`: Maximum number of results to return

Example:
```bash
python leadgen.py --size "50-200" --industry "technology" --location "San Francisco" --output "tech_leads.csv" --limit 50
```

## Output

The tool generates a CSV file with detailed company information and personalized outreach messages. Here are examples of the console output:

### Example 1: Search Results Summary
```
Search Criteria: Size=50-200, Industry=software, Location=
Leads found:
- Google (www.google.com)
- Microsoft (www.microsoft.com)
- ...
```

### Example 2: Detailed Company Information
```
Company: Google
Website: www.google.com
Employees: 10000+
Phone: +1 855 808 2978
Hunter Emails: 
- firstname.lastname@google.com
- firstname@google.com
Personalized Message: 
[AI-generated outreach message specific to the company]
```

### CSV Output Columns
- Company Name
- Website
- Industry
- Company Size
- Location
- Email Addresses
- Personalized Message
- Additional Notes

## Example Outputs

### Search Results Output
![Search Results Output](search_results_output.png)
*Figure 1: Example of search results and company information*

### Detailed Lead Information
![Detailed Lead Information](lead_details_output.png)
*Figure 2: Example of detailed lead information and outreach message*


## Troubleshooting

- If you encounter API rate limits, try reducing the limit parameter
- Ensure all required API keys are correctly set in the config file
- Check your internet connection if API calls are failing



