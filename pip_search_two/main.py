#!/usr/bin/env python3
"""
Simple PyPI package search tool
Usage: python pipsearch.py <search_terms...> [-n COUNT]
"""

import sys
import requests
import re
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_package_info(package_name):
    """Get package description from PyPI JSON API"""
    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=3)
        if response.status_code == 200:
            data = response.json()
            summary = data.get('info', {}).get('summary', 'No description available')
            # Clean up the summary
            if summary:
                summary = summary.strip()[:80]  # Limit to 80 chars
            else:
                summary = 'No description available'
            return summary
        return 'No description available'
    except:
        return 'No description available'


def search_packages(term):
    """Search PyPI simple index for packages"""
    try:
        response = requests.get("https://pypi.org/simple/", timeout=10)
        if response.status_code != 200:
            return []
        
        # Extract package names
        packages = re.findall(r'<a href="/simple/([^/]+)/">', response.text)
        
        # Handle multiple search terms
        search_words = term.lower().split()
        
        if len(search_words) == 1:
            # Single term: search for packages containing the term
            matches = [pkg for pkg in packages if search_words[0] in pkg.lower()]
        else:
            # Multiple terms: search for packages containing any of the terms
            matches = []
            for pkg in packages:
                pkg_lower = pkg.lower()
                if any(word in pkg_lower for word in search_words):
                    matches.append(pkg)
        
        # Sort: exact matches first, then matches with more terms, then alphabetical
        exact_matches = [pkg for pkg in matches if pkg.lower() == term.lower()]
        
        # For multi-term searches, prioritize packages that contain more of the terms
        if len(search_words) > 1:
            def match_score(pkg):
                pkg_lower = pkg.lower()
                score = sum(1 for word in search_words if word in pkg_lower)
                return (-score, pkg.lower())  # Negative for reverse sort, then alphabetical
            
            partial_matches = [pkg for pkg in matches if pkg.lower() != term.lower()]
            partial_matches.sort(key=match_score)
        else:
            partial_matches = sorted([pkg for pkg in matches if pkg.lower() != term.lower()])
        
        return exact_matches + partial_matches
    
    except Exception as e:
        print(f"Error searching packages: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Search PyPI packages from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s requests
  %(prog)s machine learning
  %(prog)s web scraping -n 20
  %(prog)s django rest framework --count 5
        """
    )
    
    parser.add_argument(
        'search_terms',
        nargs='+',
        help='Search terms (multiple words will be joined with spaces)'
    )
    
    parser.add_argument(
        '-n', '--count',
        type=int,
        default=10,
        help='Number of results to show (default: 10)'
    )
    
    args = parser.parse_args()
    
    # Join multiple search terms with spaces
    search_term = ' '.join(args.search_terms)
    
    # Search for packages
    packages = search_packages(search_term)
    
    if not packages:
        print("No packages found")
        return
    
    # Limit results
    packages = packages[:args.count]
    
    # Get descriptions concurrently for speed
    package_info = {}
    
    # Use ThreadPoolExecutor to fetch descriptions in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_pkg = {executor.submit(get_package_info, pkg): pkg for pkg in packages}
        
        for future in as_completed(future_to_pkg):
            pkg = future_to_pkg[future]
            try:
                description = future.result()
                package_info[pkg] = description
            except:
                package_info[pkg] = 'No description available'
    
    # Display results
    for pkg in packages:
        description = package_info.get(pkg, 'No description available')
        
        # Mark exact matches
        if pkg.lower() == search_term.lower():
            print(f"{pkg} * - {description}")
        else:
            print(f"{pkg} - {description}")


if __name__ == "__main__":
    main()