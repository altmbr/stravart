from models import format_activity_summary


def select_activity(activities):
    """Display a menu of activities and let the user select one."""
    print("\nYour recent runs:")
    print("----------------")
    
    # Show each activity with details
    for i, activity in enumerate(activities, 1):
        print(format_activity_summary(activity, i))
    
    # Get user selection
    while True:
        try:
            choice = input("\nSelect a run to generate artwork for (1-5, or 'q' to quit): ")
            if choice.lower() == 'q':
                return None
                
            choice_num = int(choice)
            if 1 <= choice_num <= len(activities):
                return activities[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(activities)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")