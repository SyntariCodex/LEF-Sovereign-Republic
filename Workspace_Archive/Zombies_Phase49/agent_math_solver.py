
import os
import csv
import pandas as pd
import time
import subprocess
import re
import sys

# Optional: Google Gemini Support
try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    # Fix path: specialists -> agents -> fulcrum -> LEF Ai
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), '.env')
    print(f"[MATH] Loading .env from: {env_path}")
    load_dotenv(env_path)
    GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
    if GOOGLE_KEY:
        genai.configure(api_key=GOOGLE_KEY)
        MODEL = genai.GenerativeModel('gemini-2.0-flash') # Verified from list
    else:
        MODEL = None
except ImportError:
    MODEL = None

class AgentMathSolver:
    def __init__(self):
        self.arena_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'arena')
        self.aimo_path = os.path.join(self.arena_path, 'ai-mathematical-olympiad-progress-prize-3')
        print("[MATH] 🧮 AgentMath Initialized.")
        
        if not MODEL:
            print("[MATH] ⚠️ No Google Gemini Key found. Solver will be lobotomized.")

    def solve_reference(self):
        """
        Iterates through reference.csv and attempts to solve problems with Reflexion.
        """
        ref_path = os.path.join(self.aimo_path, 'reference.csv')
        if not os.path.exists(ref_path):
            print(f"[MATH] 🛑 Reference file not found: {ref_path}")
            return

        df = pd.read_csv(ref_path)
        print(f"[MATH] 🤓 Attempting to solve {len(df)} Reference Problems with Reflexion...")
        
        correct = 0
        total = 0
        
        for index, row in df.iterrows():
            total += 1
            problem = row['problem']
            true_answer = int(row['answer'])
            
            print(f"\n[MATH] ➤ Problem {index+1}: {problem[:50]}...")
            
            # REFLEXION LOOP
            predicted_answer = None
            history = [] # Chat history for context
            
            for attempt in range(3):
                # 1. THINK & CODE
                code = self.generate_code(problem, history)
                if not code:
                    print(f"      [Attempt {attempt+1}] ❌ Generation Failed.")
                    break
                
                # 2. EXECUTE
                exec_result, error = self.execute_code(code)
                
                if exec_result is not None:
                    predicted_answer = exec_result
                    print(f"      [Attempt {attempt+1}] 💡 Output: {predicted_answer}")
                    break # Success!
                
                else:
                    print(f"      [Attempt {attempt+1}] ⚠️ Error: {error if error else 'No Output'}")
                    # Feed feedback
                    history.append({"role": "user", "parts": [f"Your code failed with error:\n{error}\nPlease fix it and print the integer answer."]})
            
            # 3. VERIFY
            if predicted_answer is not None and int(predicted_answer) == true_answer:
                print(f"[MATH] ✅ CORRECT! (Ans: {true_answer})")
                correct += 1
            else:
                print(f"[MATH] ❌ WRONG. Pred: {predicted_answer} | True: {true_answer}")
                
        print(f"\n[MATH] 🎓 SCORE: {correct}/{total} ({correct/total*100:.1f}%)")

    def generate_code(self, problem, history):
        if not MODEL: return None
        
        # Construct Prompt
        if not history:
            prompt = f"""
            You are a World Class Mathematician and Python Expert.
            Goal: Solve the following math problem by writing a Python script.
            
            Problem:
            {problem}
            
            Instructions:
            1. Import needed libraries (sympy, math, numpy).
            2. Write clean logic to solve the problem.
            3. PRINT the final answer as a SINGLE INTEGER on the last line.
            4. Do not print debug info, only the answer at the end.
            5. Return ONLY the python code.
            """
            chat = MODEL.start_chat(history=[])
            response = chat.send_message(prompt)
        else:
            # Continue chat for corrections
            chat = MODEL.start_chat(history=history[:-1]) # Reconstruct logic if needed, or just strict prompt
            # Actually, Gemini API `start_chat` manages state. 
            # Simplified: Just generate new content with context if API supports, 
            # but for 'flash' stateless might be safer. 
            # Let's use simple prompt chaining for now.
            
            # APPEND ERROR from history
            last_error = history[-1]['parts'][0]
            repair_prompt = f"The previous code for problem '{problem[:20]}...' failed.\n{last_error}\nRewrite the code to fix this."
            response = MODEL.generate_content(repair_prompt)

        try:
            code = response.text
            # Clean Code
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0]
            elif "```" in code:
                code = code.split("```")[1].split("```")[0]
            return code.strip()
        except Exception as e:
            print(f"[MATH] 🧠 Brain Error: {e}")
            return None

    def execute_code(self, code):
        """
        Runs code. Returns (Answer, ErrorMessage).
        """
        temp_script = os.path.join(self.aimo_path, 'temp_solver.py')
        
        # Sanitization: Ensure formatting
        if "print(" not in code:
            return None, "Code does not print answer."

        with open(temp_script, 'w') as f:
            f.write(code)
            
        try:
            result = subprocess.run(
                [sys.executable, temp_script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                err = result.stderr.strip()
                # Common: ModuleNotFoundError
                if "ModuleNotFoundError" in err:
                     # Auto-install? No, risk.
                     pass
                return None, err
                
            output = result.stdout.strip().split('\n')
            if not output: return None, "No Output captured"
            
            last_line = output[-1].strip()
            # Clean output (remove 'Answer:', etc)
            last_line = re.sub(r'[^0-9-]', '', last_line)
            
            if not last_line:
                return None, f"Output format invalid: {output[-1]}"
                
            return int(float(last_line)), None
            
        except subprocess.TimeoutExpired:
            return None, "Timeout (10s)"
        except Exception as e:
            return None, str(e)
        finally:
            if os.path.exists(temp_script):
                os.remove(temp_script)

if __name__ == "__main__":
    solver = AgentMathSolver()
    solver.solve_reference()
