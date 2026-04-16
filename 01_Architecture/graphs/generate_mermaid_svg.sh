#!/usr/bin/env bash
# generate_mermaid_svg.sh
# Generates SVG files from Mermaid .mmd files
#
# Usage:
#   ./generate_mermaid_svg.sh              # Generate all SVGs
#   ./generate_mermaid_svg.sh specific.mmd  # Generate specific file
#
# Requirements:
#   - Node.js and npm must be installed
#   - @mermaid-js/mermaid-cli must be installed globally

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js not found${NC}"
    echo "Please install Node.js: https://nodejs.org/"
    exit 1
fi

# Check for Mermaid CLI
if ! command -v mmdc &> /dev/null; then
    echo -e "${YELLOW}Mermaid CLI not found, attempting to install...${NC}"
    npm install -g @mermaid-js/mermaid-cli
fi

echo -e "${GREEN}Mermaid CLI ready${NC}"
echo ""

# Parse arguments
if [ $# -gt 0 ]; then
    # Generate specific file
    if [ -f "$1" ]; then
        mmd_file="$1"
        svg_file="${mmd_file%.mmd}.svg"
        echo -e "${YELLOW}Generating $svg_file from $mmd_file...${NC}"
        if mmdc -i "$mmd_file" -o "$svg_file" 2>/dev/null; then
            echo -e "${GREEN}✓ Generated: $svg_file${NC}"
        else
            echo -e "${RED}✗ Failed: $mmd_file${NC}"
        fi
    else
        echo -e "${RED}File not found: $1${NC}"
        exit 1
    fi
else
    # Generate all .mmd files
    MMD_COUNT=$(find . -maxdepth 1 -name "*.mmd" | wc -l | tr -d ' ')
    echo "Found $MMD_COUNT Mermaid file(s)"
    echo ""
    
    success=0
    failed=0
    
    echo -e "${YELLOW}Generating SVG files from Mermaid...${NC}"
    for mmd_file in *.mmd; do
        if [ -f "$mmd_file" ]; then
            svg_file="${mmd_file%.mmd}.svg"
            if mmdc -i "$mmd_file" -o "$svg_file" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Generated: $svg_file"
                ((success++))
            else
                echo -e "  ${RED}✗${NC} Failed: $mmd_file"
                ((failed++))
            fi
        fi
    done
    
    echo ""
    echo -e "${GREEN}Summary: $success succeeded${NC}"
    if [ $failed -gt 0 ]; then
        echo -e "${RED}         $failed failed${NC}"
    fi
fi
