def analyze_run_type(activity) -> str:
    """
    Analyze the activity's split data to determine the type of run.
    
    Different run types have characteristic split patterns:
    - Long Run: > 5 miles and at or slower than 7:30 pace
    - Intervals: Clear alternating pattern of fast/slow segments
    - Tempo Run: Between 3-10 miles at > 7:30 pace and relatively consistent
    """
    # Initialize as fallback
    run_type = "run"
    
    try:
        # First check run name for common interval workout indicators
        if hasattr(activity, 'name'):
            name_lower = activity.name.lower()
            interval_keywords = ['interval', 'repeat', 'x', '400', '800', '1000', '1200', '1600', 'mile repeat', 'hiit']
            
            # Check for high intensity interval workout keywords
            hiit_keywords = ['hiit', 'high intensity', 'sprint', 'tabata']
            for keyword in hiit_keywords:
                if keyword in name_lower:
                    return "High Intensity Interval Training"
            
            # Check if any interval keywords are in the run name
            for keyword in interval_keywords:
                if keyword in name_lower:
                    return "Interval Run"
        
        # Get splits if available
        splits = []
        if hasattr(activity, 'splits_metric') and activity.splits_metric:
            splits = activity.splits_metric
        
        # Not enough data for analysis
        if len(splits) < 3:
            return run_type
            
        # Extract pace data for each split
        paces = []
        for split in splits:
            if hasattr(split, 'average_speed') and split.average_speed > 0:
                # Convert speed to pace (seconds per km)
                pace_secs_per_km = 1000 / split.average_speed
                paces.append(pace_secs_per_km)
        
        if not paces:
            return run_type
            
        # Calculate stats for analysis
        avg_pace = sum(paces) / len(paces)
        pace_variation = max(paces) - min(paces)
        pace_std_dev = (sum((p - avg_pace) ** 2 for p in paces) / len(paces)) ** 0.5
        
        # Calculate pace changes between consecutive splits
        pace_changes = [abs(paces[i] - paces[i-1]) for i in range(1, len(paces))]
        avg_change = sum(pace_changes) / len(pace_changes) if pace_changes else 0
        
        # Detect pattern of alternating fast/slow for intervals
        alternating_pattern = True
        for i in range(2, len(paces)):
            # If three consecutive splits don't show alternating pattern
            if (paces[i] > paces[i-1] and paces[i-1] > paces[i-2]) or \
               (paces[i] < paces[i-1] and paces[i-1] < paces[i-2]):
                alternating_pattern = False
                break
        
        # Get total distance in miles
        distance_miles = activity.distance / 1609.34
        
        # Convert avg pace to min/mile for comparison (7:30 pace = 450 seconds per mile)
        avg_pace_secs_per_mile = avg_pace * 1.60934  # Convert secs/km to secs/mile
        
        # New decision logic based on the specified criteria
        if alternating_pattern and pace_variation > avg_pace * 0.2:
            # Clear alternating pattern of fast/slow segments
            run_type = "Interval Run"
        elif distance_miles > 5 and avg_pace_secs_per_mile >= 450:
            # > 5 miles and at or slower than 7:30 min/mile
            run_type = "Easy Run"
        elif 3 <= distance_miles <= 10 and avg_pace_secs_per_mile < 450 and pace_std_dev < avg_pace * 0.1:
            # Between 3-10 miles at faster than 7:30 pace and relatively consistent
            run_type = "Tempo Run"
        elif distance_miles > 10 and avg_pace_secs_per_mile >= 450:
            # > 10 miles and at or faster than 7:30 pace
            run_type = "Long Run"
        elif distance_miles <= 5 and avg_pace_secs_per_mile < 450:
            # Short and fast runs that aren't intervals
            run_type = "Tempo Run" 
        
        return run_type
    except Exception as e:
        print(f"Error analyzing run type: {e}")
        return run_type