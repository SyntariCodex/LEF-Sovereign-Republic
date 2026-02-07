import datetime

def main():
    """
    Prints a success message along with the current timestamp.
    """
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("---------------------------------------------")
    print("Fulcrum Hello World Script Executed Successfully!")
    print(f"Current Time: {current_time}")
    print("---------------------------------------------")

if __name__ == "__main__":
    main()