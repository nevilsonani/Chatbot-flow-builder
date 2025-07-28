import argparse
import os
import requests
from bs4 import BeautifulSoup
import openai
import csv
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load config from environment variables
def load_config():
    return {
        "apollo_api_key": os.getenv("APOLLO_API_KEY"),
        "google_sheets_api_key": os.getenv("GOOGLE_SHEETS_API_KEY"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "hunter_api_key": os.getenv("HUNTER_API_KEY"),
        "default_search": {
            "company_size": os.getenv("DEFAULT_COMPANY_SIZE", "50-200"),
            "industry": os.getenv("DEFAULT_INDUSTRY", "software"),
            "location": os.getenv("DEFAULT_LOCATION", "")
        }
    }

def apollo_search_companies(api_key, company_size, industry, location):
    url = "https://api.apollo.io/v1/organizations/search"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": api_key
    }
    payload = {
        "organization_sizes": [company_size],
        "industries": [industry],
    }
    if location:
        payload["locations"] = [location]
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Apollo API error: {response.status_code} {response.text}")
        return []
    data = response.json()
    results = []
    for org in data.get("organizations", []):
        results.append({
            "name": org.get("name"),
            "website": org.get("website_url"),
            "employee_count": org.get("estimated_num_employees"),
        })
    return results

def apollo_enrich_company(api_key, domain, debug=False):
    url = "https://api.apollo.io/v1/organizations/enrich"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": api_key
    }
    payload = {"domain": domain}
    response = requests.post(url, json=payload, headers=headers)
    if debug:
        print(f"[DEBUG] Enrich response for {domain}: {response.text}")
    if response.status_code != 200:
        return {}
    return response.json().get("organization", {})

def apollo_top_people(api_key, domain, debug=False):
    url = "https://api.apollo.io/v1/mixed_people/organization_top_people"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": api_key
    }
    payload = {"organization_domain": domain}
    response = requests.post(url, json=payload, headers=headers)
    if debug:
        print(f"[DEBUG] Top people response for {domain}: {response.text}")
    if response.status_code != 200:
        return []
    return response.json().get("people", [])

def apollo_search_contacts(api_key, domain, debug=False):
    url = "https://api.apollo.io/v1/contacts/search"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "X-Api-Key": api_key
    }
    payload = {"organization_domains": [domain], "page": 1}
    response = requests.post(url, json=payload, headers=headers)
    if debug:
        print(f"[DEBUG] Contacts response for {domain}: {response.text}")
    if response.status_code != 200:
        return []
    return response.json().get("contacts", [])

def hunter_get_emails(api_key, domain):
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []
        data = response.json()
        emails = data.get('data', {}).get('emails', [])
        return [f"{e.get('value','')} ({e.get('type','')})" for e in emails]
    except Exception:
        return []

def hunter_company_enrich(api_key, domain):
    url = f"https://api.hunter.io/v2/companies/find?domain={domain}&api_key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return {}
        return response.json().get('data', {})
    except Exception:
        return {}

def scrape_company_insights(website_url):
    insights = []
    if not website_url:
        return insights
    try:
        resp = requests.get(website_url, timeout=8)
        if resp.status_code != 200:
            return insights
        soup = BeautifulSoup(resp.text, 'html.parser')
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            insights.append(meta_desc['content'].strip())
        about = soup.find(lambda tag: tag.name in ['section', 'div'] and 'about' in (tag.get('id','')+tag.get('class','')).lower())
        if about:
            about_text = about.get_text(separator=' ', strip=True)
            if about_text:
                insights.append(about_text[:200])
        for kw in ['product', 'service', 'solution']:
            prod = soup.find(lambda tag: tag.name in ['section', 'div'] and kw in (tag.get('id','')+tag.get('class','')).lower())
            if prod:
                prod_text = prod.get_text(separator=' ', strip=True)
                if prod_text:
                    insights.append(prod_text[:200])
        if len(insights) < 2:
            for p in soup.find_all('p'):
                text = p.get_text(separator=' ', strip=True)
                if text and len(text) > 40:
                    insights.append(text[:200])
                if len(insights) >= 3:
                    break
        return insights[:3]
    except Exception as e:
        return insights

def generate_personalized_message(openai_api_key, company_name, insights, hardware_context="As a hardware computer store, we offer tailored solutions for business computing needs, from workstations to networking."):
    import openai
    openai.api_key = openai_api_key
    prompt = f"""
You are a professional B2B sales representative. Write a concise, personalized outreach email to the company below. Reference their business context and suggest how your hardware solutions can help them. Be specific, professional, and relevant.

Company: {company_name}
Key Insights: {', '.join(insights) if insights else 'N/A'}
Your Business: {hardware_context}

Email:
"""
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional B2B sales representative."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=180,
            temperature=0.7,
            n=1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback to template if OpenAI fails (quota or other error)
        insight_text = (', '.join(insights) if insights else 'your business')
        return f"Hello {company_name} team,\n\nI noticed {insight_text}. As a hardware computer store, we offer tailored solutions that could help your business grow. If you are interested in upgrading your computing infrastructure or need reliable hardware support, let's connect!\n\nBest regards,\n[Your Name]"

def save_to_csv(leads, filename="leads_output.csv"):
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Company Name", "Website", "Employee Count", "Company Phone", "Company Email", "Address", "Social Links", "Insights", "Top People", "Contacts", "Hunter Emails", "Hunter Legal Name", "Hunter Phones", "Hunter Company Emails", "Hunter Industry", "Hunter Tags", "Hunter Founded", "Hunter Location", "Hunter Tech", "Outreach Message"
        ])
        for lead in leads:
            writer.writerow([
                lead['name'],
                lead['website'],
                lead['employee_count'],
                lead.get('company_phone', 'N/A'),
                lead.get('company_email', 'N/A'),
                lead.get('address', 'N/A'),
                lead.get('social_links', 'N/A'),
                " | ".join(lead['insights']) if lead['insights'] else 'N/A',
                lead.get('top_people', 'N/A'),
                lead.get('contacts', 'N/A'),
                " | ".join(lead.get('hunter_emails', [])) if lead.get('hunter_emails') else 'N/A',
                lead.get('hunter_legal_name', 'N/A'),
                lead.get('hunter_phones', 'N/A'),
                lead.get('hunter_company_emails', 'N/A'),
                lead.get('hunter_industry', 'N/A'),
                lead.get('hunter_tags', 'N/A'),
                lead.get('hunter_founded', 'N/A'),
                lead.get('hunter_location', 'N/A'),
                lead.get('hunter_tech', 'N/A'),
                lead['message']
            ])

def main():
    config = load_config()
    parser = argparse.ArgumentParser(description="Lead Generation Automation Script")
    parser.add_argument('--company_size', type=str, default=config['default_search']['company_size'])
    parser.add_argument('--industry', type=str, default=config['default_search']['industry'])
    parser.add_argument('--location', type=str, default=config['default_search']['location'])
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to print raw API responses')
    args = parser.parse_args()
    print(f"Search Criteria: Size={args.company_size}, Industry={args.industry}, Location={args.location}")

    # Apollo API integration
    leads_raw = apollo_search_companies(
        config['apollo_api_key'], args.company_size, args.industry, args.location
    )
    print("\nLeads found:")
    leads = []
    count_with_contacts = 0
    count_with_top_people = 0
    for lead in leads_raw:
        print(f"- {lead['name']} | {lead['website']} | Employees: {lead['employee_count']}")
        domain = lead['website'].replace('http://', '').replace('https://', '').split('/')[0] if lead['website'] else ''
        enrich = apollo_enrich_company(config['apollo_api_key'], domain, args.debug) if domain else {}
        company_phone = enrich.get('phone', 'N/A') or 'N/A'
        company_email = enrich.get('email', 'N/A') or 'N/A'
        address = enrich.get('address', 'N/A') or 'N/A'
        socials = []
        for key in ['linkedin_url', 'facebook_url', 'twitter_url', 'crunchbase_url']:
            if enrich.get(key):
                socials.append(f"{key.replace('_url','').capitalize()}: {enrich[key]}")
        social_links = ' | '.join(socials) if socials else 'N/A'
        top_people_list = apollo_top_people(config['apollo_api_key'], domain, args.debug) if domain else []
        if top_people_list:
            count_with_top_people += 1
        top_people = ' | '.join([f"{p.get('name','N/A')} ({p.get('title','N/A')})" for p in top_people_list]) if top_people_list else 'N/A'
        contacts_list = apollo_search_contacts(config['apollo_api_key'], domain, args.debug) if domain else []
        if contacts_list:
            count_with_contacts += 1
        contacts = ' | '.join([f"{c.get('first_name','N/A')} {c.get('last_name','N/A')} ({c.get('title','N/A')}) {c.get('email','N/A')} {c.get('phone','N/A')}" for c in contacts_list]) if contacts_list else 'N/A'
        insights = scrape_company_insights(lead['website'])
        # Hunter emails
        hunter_emails = hunter_get_emails(config['hunter_api_key'], domain) if domain else []
        # Hunter company enrichment
        hunter_enrich = hunter_company_enrich(config['hunter_api_key'], domain) if domain else {}
        hunter_phones = ' | '.join(hunter_enrich.get('site', {}).get('phoneNumbers', [])) if hunter_enrich.get('site', {}) else 'N/A'
        hunter_company_emails = ' | '.join(hunter_enrich.get('site', {}).get('emailAddresses', [])) if hunter_enrich.get('site', {}) else 'N/A'
        hunter_legal_name = hunter_enrich.get('legalName', 'N/A')
        hunter_tags = ' | '.join(hunter_enrich.get('tags', [])) if hunter_enrich.get('tags') else 'N/A'
        hunter_founded = hunter_enrich.get('foundedYear', 'N/A')
        hunter_location = hunter_enrich.get('location', 'N/A')
        hunter_industry = hunter_enrich.get('category', {}).get('industry', 'N/A') if hunter_enrich.get('category') else 'N/A'
        hunter_tech = ' | '.join(hunter_enrich.get('tech', [])) if hunter_enrich.get('tech') else 'N/A'
        print(f"  Company Phone: {company_phone}")
        print(f"  Company Email: {company_email}")
        print(f"  Address: {address}")
        print(f"  Social Links: {social_links}")
        print(f"  Insights: {(' | '.join(insights)) if insights else 'N/A'}")
        print(f"  Top People: {top_people}")
        print(f"  Contacts: {contacts}")
        print(f"  Hunter Emails: {(' | '.join(hunter_emails)) if hunter_emails else 'N/A'}")
        print(f"  Hunter Legal Name: {hunter_legal_name}")
        print(f"  Hunter Phones: {hunter_phones}")
        print(f"  Hunter Company Emails: {hunter_company_emails}")
        print(f"  Hunter Industry: {hunter_industry}")
        print(f"  Hunter Tags: {hunter_tags}")
        print(f"  Hunter Founded: {hunter_founded}")
        print(f"  Hunter Location: {hunter_location}")
        print(f"  Hunter Tech: {hunter_tech}")
        message = generate_personalized_message(
            config['openai_api_key'], lead['name'], insights
        )
        print("  Outreach Message:")
        print(f"    {message}\n")
        leads.append({
            'name': lead['name'],
            'website': lead['website'],
            'employee_count': lead['employee_count'],
            'company_phone': company_phone,
            'company_email': company_email,
            'address': address,
            'social_links': social_links,
            'insights': insights,
            'top_people': top_people,
            'contacts': contacts,
            'hunter_emails': hunter_emails,
            'hunter_legal_name': hunter_legal_name,
            'hunter_phones': hunter_phones,
            'hunter_company_emails': hunter_company_emails,
            'hunter_industry': hunter_industry,
            'hunter_tags': hunter_tags,
            'hunter_founded': hunter_founded,
            'hunter_location': hunter_location,
            'hunter_tech': hunter_tech,
            'message': message
        })
    # Output to CSV only
    save_to_csv(leads)
    # Print summary
    print(f"\nSummary: {len(leads)} companies processed.")
    print(f"  Companies with contacts: {count_with_contacts}")
    print(f"  Companies with top people: {count_with_top_people}")
    print(f"  Output saved to leads_output.csv\n")

if __name__ == "__main__":
    main() 