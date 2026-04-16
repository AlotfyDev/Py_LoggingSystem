#!/usr/bin/env bash
# generate_all_svg.sh
# Generates SVG files from all DOT files in the graphs directory
#
# Usage:
#   ./generate_all_svg.sh           # Generate all SVGs
#   ./generate_all_svg.sh --png    # Also generate PNGs
#   ./generate_all_svg.sh --pdf    # Also generate PDFs
#
# Requirements:
#   - Graphviz must be installed (dot command)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for Graphviz
if ! command -v dot &> /dev/null; then
    echo -e "${RED}Error: Graphviz 'dot' command not found${NC}"
    echo ""
    echo "Please install Graphviz:"
    echo "  macOS:    brew install graphviz"
    echo "  Linux:    sudo apt-get install graphviz"
    echo "  Windows:  https://graphviz.org/download/"
    exit 1
fi

echo -e "${GREEN}Graphviz found: $(dot -V 2>&1)${NC}"
echo ""

# Count DOT files
DOT_COUNT=$(find . -maxdepth 1 -name "*.dot" | wc -l | tr -d ' ')
echo "Found $DOT_COUNT DOT file(s)"
echo ""

# Parse arguments
GENERATE_PNG=false
GENERATE_PDF=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --png)
            GENERATE_PNG=true
            shift
            ;;
        --pdf)
            GENERATE_PDF=true
            shift
            ;;
        --all)
            GENERATE_PNG=true
            GENERATE_PDF=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--png] [--pdf] [--all]"
            exit 1
            ;;
    esac
done

success=0
failed=0

# Generate SVGs
echo -e "${YELLOW}Generating SVG files...${NC}"
for dot_file in *.dot; do
    if [ -f "$dot_file" ]; then
        svg_file="${dot_file%.dot}.svg"
        if dot -Tsvg "$dot_file" -o "$svg_file" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Generated: $svg_file"
            ((success++))
        else
            echo -e "  ${RED}✗${NC} Failed: $dot_file"
            ((failed++))
        fi
    fi
done

# Generate PNGs if requested
if [ "$GENERATE_PNG" = true ]; then
    echo ""
    echo -e "${YELLOW}Generating PNG files...${NC}"
    for dot_file in *.dot; do
        if [ -f "$dot_file" ]; then
            png_file="${dot_file%.dot}.png"
            if dot -Tpng "$dot_file" -o "$png_file" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Generated: $png_file"
                ((success++))
            else
                echo -e "  ${RED}✗${NC} Failed: $dot_file"
                ((failed++))
            fi
        fi
    done
fi

# Generate PDFs if requested
if [ "$GENERATE_PDF" = true ]; then
    echo ""
    echo -e "${YELLOW}Generating PDF files...${NC}"
    for dot_file in *.dot; do
        if [ -f "$dot_file" ]; then
            pdf_file="${dot_file%.dot}.pdf"
            if dot -Tpdf "$dot_file" -o "$pdf_file" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Generated: $pdf_file"
                ((success++))
            else
                echo -e "  ${RED}✗${NC} Failed: $dot_file"
                ((failed++))
            fi
        fi
    done
fi

echo ""
echo -e "${GREEN}Summary: $success succeeded${NC}" 
if [ $failed -gt 0 ]; then
    echo -e "${RED}         $failed failed${NC}"
fi
