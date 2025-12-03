# from concurrent.futures import ThreadPoolExecutor
# import aiohttp, asyncio

# async def process_audio_async(session_id: str, api_url: str = "http://localhost:5050/process_audio"):
#     payload = {"session_id": session_id}
    
#     async with aiohttp.ClientSession() as session:
#         async with session.post(api_url, json=payload) as response:
#             if response.status == 200:
#                 return await response.json()
#             else:
#                 error = await response.text()
#                 raise f"API Error: {error}"

# def process_audio_threaded(session_id: str):
#     with ThreadPoolExecutor() as executor:
#         future = executor.submit(
#             lambda: asyncio.run(process_audio_async(session_id)))
#         return future.result()
    


# async def process_scrolling_async(session_id: str, api_url: str = "http://localhost:5050/process_scrolling"):
#     payload = {"session_id": session_id}
    
#     async with aiohttp.ClientSession() as session:
#         async with session.post(api_url, json=payload) as response:
#             if response.status == 200:
#                 return await response.json()
#             else:
#                 error = await response.text()
#                 raise f"API Error: {error}"

# def process_scrolling_threaded(session_id: str):
#     with ThreadPoolExecutor() as executor:
#         future = executor.submit(
#             lambda: asyncio.run(process_scrolling_async(session_id)))
#         return future.result()



# async def process_mouseMovement_async(session_id: str, api_url: str = "http://localhost:5050/process_mouseMovement"):
#     payload = {"session_id": session_id}
    
#     async with aiohttp.ClientSession() as session:
#         async with session.post(api_url, json=payload) as response:
#             if response.status == 200:
#                 return await response.json()
#             else:
#                 error = await response.text()
#                 raise f"API Error: {error}"

# def process_mouseMovement_threaded(session_id: str):
#     with ThreadPoolExecutor() as executor:
#         future = executor.submit(
#             lambda: asyncio.run(process_mouseMovement_async(session_id)))
#         return future.result()


import eventlet
import requests  # Using synchronous requests instead of aiohttp
from concurrent.futures import ThreadPoolExecutor

# Apply eventlet monkey patching (important for async compatibility)
eventlet.monkey_patch()

def process_audio(session_id: str, api_url: str = "http://localhost:5050/process_audio"):
    payload = {"session_id": session_id}
    response = requests.post(api_url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error: {response.text}")

def process_audio_threaded(session_id: str):
    with ThreadPoolExecutor() as executor:
        future = executor.submit(process_audio, session_id)
        return future.result()
    

def process_keystroke_sensors(session_id: str, api_url: str = "http://localhost:5050/process_keystroke_sensors"):
    payload = {"session_id": session_id}
    response = requests.post(api_url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error: {response.text}")

def process_keystroke_sensors_threaded(session_id: str):
    with ThreadPoolExecutor() as executor:
        future = executor.submit(process_keystroke_sensors, session_id)
        return future.result()

def process_scrolling(session_id: str, api_url: str = "http://localhost:5050/process_scrolling"):
    payload = {"session_id": session_id}
    response = requests.post(api_url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error: {response.text}")

def process_scrolling_threaded(session_id: str):
    with ThreadPoolExecutor() as executor:
        future = executor.submit(process_scrolling, session_id)
        return future.result()

def process_mouseMovement(session_id: str, api_url: str = "http://localhost:5050/process_mouseMovement"):
    payload = {"session_id": session_id}
    response = requests.post(api_url, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error: {response.text}")

def process_mouseMovement_threaded(session_id: str):
    with ThreadPoolExecutor() as executor:
        future = executor.submit(process_mouseMovement, session_id)
        return future.result()