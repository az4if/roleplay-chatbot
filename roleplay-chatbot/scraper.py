import requests
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin
import json
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set headers to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.google.com/',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
}

def clean_text(text):
    """Clean and format text from wiki"""
    text = re.sub(r'\[\d+\]', '', text)  # Remove references [1]
    text = re.sub(r'\{\{.*?\}\}', '', text)  # Remove templates {{...}}
    text = re.sub(r'<.*?>', '', text)  # Remove HTML tags
    text = text.replace('\n', ' ').replace('\t', ' ')  # Replace newlines and tabs
    text = re.sub(r'\s+', ' ', text).strip()  # Collapse multiple spaces
    return text

def extract_image_url(soup, base_url):
    """Extract character image URL from the wiki page"""
    try:
        # Try various methods to find character image
        sources = [
            ('.pi-image-thumbnail', 'src'),
            ('.mw-parser-output img', 'src'),
            ('meta[property="og:image"]', 'content'),
            ('meta[name="twitter:image"]', 'content'),
            ('.image img', 'src'),
            ('.thumbimage', 'src'),
            ('.character-image img', 'src'),
            ('.infobox-image img', 'src')
        ]
        
        for selector, attr in sources:
            element = soup.select_one(selector)
            if element and element.get(attr):
                img_url = element[attr]
                # Handle relative URLs
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = urljoin(base_url, img_url)
                return img_url
    except Exception as e:
        logger.error(f"Error extracting image: {e}")
    return None

def extract_speech_style(soup):
    """Extract character speech patterns from the page"""
    speech_style = ""
    
    # Look for specific sections
    section_keywords = [
        'speech', 'dialogue', 'quotes', 'voice', 'talking', 
        'personality', 'character', 'traits', 'style', 'catchphrase'
    ]
    
    # Look for quotes in the page
    quotes = []
    quote_selectors = [
        'blockquote',
        '.quote',
        'dl dd',
        '.poem',
        'div.quote',
        '.quote-box',
        '.citation',
        '.dialogue'
    ]
    
    for selector in quote_selectors:
        for element in soup.select(selector):
            text = clean_text(element.get_text())
            if len(text) > 10 and len(text) < 500:
                quotes.append(text)
    
    # Use first 3 quotes if found
    if quotes:
        speech_style = "Character is known to say things like:\n"
        speech_style += "\n".join([f"- {q}" for q in quotes[:3]])
        return speech_style
    
    # If no quotes, look for personality sections
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        heading_text = heading.text.lower()
        if any(kw in heading_text for kw in section_keywords):
            content = ""
            next_node = heading.find_next_sibling()
            
            while next_node and next_node.name not in ['h2', 'h3', 'h4']:
                if next_node.name == 'p':
                    content += clean_text(next_node.text) + "\n"
                elif next_node.name == 'ul':
                    for li in next_node.find_all('li'):
                        content += "- " + clean_text(li.text) + "\n"
                next_node = next_node.find_next_sibling()
            
            if content:
                return content[:1000]  # Return first 1000 characters
    
    return ""

def extract_personality(soup):
    """Extract detailed personality information"""
    personality = ""
    personality_keywords = [
        'personality', 'character', 'traits', 'behavior',
        'appearance', 'abilities', 'skills', 'background'
    ]
    
    # Try to find personality section
    for heading in soup.find_all(['h2', 'h3']):
        heading_text = heading.text.lower()
        if any(kw in heading_text for kw in personality_keywords):
            content = ""
            next_node = heading.find_next_sibling()
            
            while next_node and next_node.name not in ['h2', 'h3']:
                if next_node.name == 'p':
                    content += clean_text(next_node.text) + "\n"
                elif next_node.name == 'ul':
                    for li in next_node.find_all('li'):
                        content += "- " + clean_text(li.text) + "\n"
                next_node = next_node.find_next_sibling()
            
            if content:
                personality += f"## {heading.text}\n{content}\n"
    
    return personality.strip()

def scrape_character_data(url):
    """Scrape character data from a wiki URL"""
    try:
        logger.info(f"Scraping character data from: {url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract character name
        name_element = soup.find('h1', {'class': 'page-header__title'})
        if not name_element:
            name_element = soup.find('h1', {'id': 'firstHeading'})
        if not name_element:
            name_element = soup.find('h1', {'class': 'page-title__text'})
        
        name = name_element.text.strip() if name_element else "Character"
        logger.info(f"Character name: {name}")
        
        # Extract description
        description = ""
        content = soup.find('div', {'class': 'mw-parser-output'})
        if content:
            # Get first 3 paragraphs
            paragraphs = content.find_all('p', recursive=False)
            valid_paragraphs = []
            for p in paragraphs:
                text = clean_text(p.text)
                if text and len(text) > 50:
                    valid_paragraphs.append(text)
                if len(valid_paragraphs) >= 3:
                    break
            description = '\n'.join(valid_paragraphs)
            
            # If not enough content, try alternative approach
            if len(description) < 100:
                sections = content.find_all(['p', 'h2', 'h3'])
                current_section = ""
                for element in sections:
                    if element.name == 'p':
                        current_section += clean_text(element.text) + "\n"
                    elif element.name in ['h2', 'h3']:
                        if len(current_section) > 100:
                            description = current_section
                            break
                        current_section = ""
        
        # Extract personality
        personality = extract_personality(soup)
        if not personality and description:
            personality = description[:1000]
        
        # Extract speech style
        speech_style = extract_speech_style(soup)
        
        # Extract image URL
        image_url = extract_image_url(soup, url)
        logger.info(f"Image URL found: {image_url}")
        
        return {
            'name': name,
            'description': description,
            'personality': personality,
            'speech_style': speech_style,
            'image_url': image_url,
            'source_url': url
        }
    
    except Exception as e:
        logger.error(f"Error scraping character data: {e}")
        return {
            'name': "Character",
            'description': "Failed to load character data",
            'personality': "",
            'speech_style': "",
            'image_url': "",
            'source_url': url
        }

def enhance_character_data(character_data):
    """Enhance character data with additional sources"""
    name = character_data['name']
    
    # Skip enhancement if we already have good data
    if len(character_data['description']) > 300 and character_data['image_url']:
        return character_data
    
    logger.info(f"Enhancing character data for: {name}")
    
    # Try to get character data from Wikipedia
    try:
        wikipedia_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts|pageimages&exintro&explaintext&titles={name}"
        response = requests.get(wikipedia_url, timeout=5)
        data = response.json()
        
        # Extract Wikipedia data
        pages = data.get('query', {}).get('pages', {})
        for page in pages.values():
            if 'extract' in page:
                # Add to description if we don't have enough
                if len(character_data['description']) < 300:
                    character_data['description'] += "\n\n" + page['extract'][:500]
                
                # Get image from Wikipedia if not found
                if not character_data['image_url'] and 'thumbnail' in page:
                    character_data['image_url'] = page['thumbnail']['source']
                    logger.info(f"Added Wikipedia image: {character_data['image_url']}")
    except Exception as e:
        logger.error(f"Wikipedia enhancement failed: {e}")
    
    # Try to get quotes from QuoteFancy
    try:
        if not character_data['speech_style']:
            quote_url = f"https://quotefancy.com/api/search?query={name}&page=1"
            response = requests.get(quote_url, timeout=5)
            quotes_data = response.json()
            
            if quotes_data.get('quotes'):
                character_data['speech_style'] = "Character is known for quotes like:\n"
                for quote in quotes_data['quotes'][:3]:
                    character_data['speech_style'] += f"- {quote['content']}\n"
                logger.info("Added quotes from QuoteFancy")
    except Exception as e:
        logger.error(f"Quote enhancement failed: {e}")
    
    # Try to get data from Character Wiki
    try:
        if len(character_data['personality']) < 500:
            search_url = f"https://characterprofile.fandom.com/wiki/Special:Search?query={name}"
            response = requests.get(search_url, headers=HEADERS, timeout=5)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find first result
            result = soup.select_one('.unified-search__result__content')
            if result:
                result_url = result.find('a')['href']
                logger.info(f"Found character profile at: {result_url}")
                
                # Scrape the character profile
                profile_response = requests.get(result_url, headers=HEADERS, timeout=5)
                profile_soup = BeautifulSoup(profile_response.content, 'html.parser')
                
                # Extract personality
                personality_section = profile_soup.select_one('#Personality')
                if personality_section:
                    personality_content = ""
                    next_node = personality_section.find_next_sibling()
                    while next_node and next_node.name != 'h2':
                        if next_node.name == 'p':
                            personality_content += clean_text(next_node.text) + "\n"
                        elif next_node.name == 'ul':
                            for li in next_node.find_all('li'):
                                personality_content += "- " + clean_text(li.text) + "\n"
                        next_node = next_node.find_next_sibling()
                    
                    if personality_content:
                        character_data['personality'] += "\n\n" + personality_content
                        logger.info("Added personality from Character Wiki")
                
                # Extract image if missing
                if not character_data['image_url']:
                    image = profile_soup.select_one('.pi-image-thumbnail')
                    if image:
                        character_data['image_url'] = image['src']
                        logger.info(f"Added image from Character Wiki: {character_data['image_url']}")
    except Exception as e:
        logger.error(f"Character Wiki enhancement failed: {e}")
    
    # Final fallbacks
    if not character_data['image_url']:
        character_data['image_url'] = ""
    
    if not character_data['speech_style']:
        character_data['speech_style'] = "No specific speech style information available"
    
    return character_data