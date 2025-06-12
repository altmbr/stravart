#!/bin/bash
# Test runner for StravaRunArt

echo "🧪 Running StravaRunArt tests..."
echo "================================"

# Run the test
python test_main.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "📊 Test artifacts:"
    echo "  - Log file: test_run.log"
    echo "  - Generated images: test_generated_images/"
else
    echo ""
    echo "❌ Tests failed! Check test_run.log for details"
    exit 1
fi