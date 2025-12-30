#!/usr/bin/env python3
"""
Simple PyPI package search tool
Usage: python pipsearch.py <search_term> [limit]
"""

import sys
import requests
import re
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
        
        # Filter packages containing search term (case insensitive)
        matches = [pkg for pkg in packages if term.lower() in pkg.lower()]
        
        # Sort: exact matches first, then alphabetical
        exact_matches = [pkg for pkg in matches if pkg.lower() == term.lower()]
        partial_matches = [pkg for pkg in matches if pkg.lower() != term.lower()]
        
        return exact_matches + sorted(partial_matches)
    
    except Exception as e:
        print(f"Error searching packages: {e}")
        return []


def main():
    if len(sys.argv) < 2:
        print("Usage: python pipsearch.py <search_term> [limit]")
        print("Examples:")
        print("  python pipsearch.py requests")
        print("  python pipsearch.py django 20")
        sys.exit(1)
    
    search_term = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 15
    
    print(f"Searching PyPI for: {search_term}")
    
    # Search for packages
    packages = search_packages(search_term)
    
    if not packages:
        print("No packages found")
        return
    
    # Limit results
    packages = packages[:limit]
    
    print(f"Found {len(packages)} packages:")
    print()
    
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
    for i, pkg in enumerate(packages, 1):
        description = package_info.get(pkg, 'No description available')
        
        # Mark exact matches
        if pkg.lower() == search_term.lower():
            print(f"{i:2d}. {pkg} * - {description}")
        else:
            print(f"{i:2d}. {pkg} - {description}")


if __name__ == "__main__":
    main()