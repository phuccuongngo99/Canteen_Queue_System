#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 10 17:07:32 2019

@author: Phuc Cuong Ngo
"""
import os
import time
import pickle
import argparse
from PIL import Image, ImageFilter
from picamera import PiCamera
from picamera.array import PiRGBArray
from apiclient import errors
from apiclient.http import MediaFileUpload
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# ...

parser = argparse.ArgumentParser()
parser.add_argument("--blur", help="degree of blur")
args = parser.parse_args()
blur_degree = int(args.blur)

def insert_file(service, title, description, parent_id, mime_type, filename):
  """Copied from Google Drive API Documentation"""
  """Insert new file.
  
  Args:
    service: Drive API service instance.
    title: Title of the file to insert, including the extension.
    description: Description of the file to insert.
    parent_id: Parent folder's ID.
    mime_type: MIME type of the file to insert.
    filename: Filename of the file to insert.
  Returns:
    Inserted file metadata if successful, None otherwise.
  """
  media_body = MediaFileUpload(filename, mimetype=mime_type, resumable=True)
  body = {
    'title': title,
    'description': description,
    'mimeType': mime_type
  }
  # Set the parent folder.
  if parent_id:
    body['parents'] = [{'id': parent_id}]

  try:
    file = service.files().insert(
        body=body,
        media_body=media_body).execute()

    # Uncomment the following line to print the File ID
    # print 'File ID: %s' % file['id']

    return file
  except errors.HttpError as error:
    print('An error occurred: %s' % error)
    return None

def capture_and_blur(blur_degree):
  """Blurring image for privacy reason. Students should only see
     how crowded the canteen is, not the the identity of other students.

  Args: 
    blur_degree: Gaussian blur radius
  """
  camera.capture(rawCapture, 'rgb')
  rawCapture.truncate(0)
  latest_array = rawCapture.array
  latest_img = Image.fromarray(latest_array)
  img_blur = latest_img.filter(ImageFilter.GaussianBlur(radius=blur_degree))
  img_blur.save('latest_img.jpg')

def html_update(image_id):
  """ Update new link to the latest image to website html file

  Args:
    image_id: Google Drive ID of the image
  """
  new_href = "https://drive.google.com/file/d/%s/view"%str(image_id)
  soup = BeautifulSoup(open(html_file), "html.parser")

  jc_link = soup('a')[0]
  jc_link['href'] = new_href
  with open(html_file, "w") as file:
      file.write(str(soup))

def print_files_in_folder(service, folder_id):
  img_id_list = []
  """Print files belonging to a folder.

  Args:
    service: Drive API service instance.
    folder_id: ID of the folder to print files from.
  """
  page_token = None
  while True:
    try:
      param = {"orderBy":"createdDate",
               "maxResults": 2
               }
      if page_token:
        param['pageToken'] = page_token
      children = service.children().list(
          folderId=folder_id, **param).execute()

      for child in children.get('items', []):
        #print('File Id: %s' % child['id'])
        img_id_list.append(child['id'])
      page_token = children.get('nextPageToken')
      if not page_token:
          return img_id_list
          break
    except errors.HttpError as error:
      print('An error occurred: %s' % error)
      break

def delete(service, file_id):
  """ Delete old images on Google Drive Folder
  Args:
    service: Google Drive service
    file_id: File id of the old image
  """
    service.files().delete(fileId=file_id).execute()

###Setting up Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
  if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
  else:
      flow = InstalledAppFlow.from_client_secrets_file(
          'credentials.json', SCOPES)
      creds = flow.run_local_server()
  # Save the credentials for the next run
  with open('token.pickle', 'wb') as token:
      pickle.dump(creds, token)

service = build('drive', 'v2', credentials=creds)
mimeType = 'application/vnd.google-apps.folder'

###Setting up camera
camera = PiCamera()
camera.resolution = (1280,720)
camera.sharpness = 100
rawCapture = PiRGBArray(camera)

folder = 'jc' #JC stands for Junior College cantee, 1 of 4 canteen in our school
folder_id = '1jiv5j82OiUATrkG00CCdK50_iMMUNJ4F' #shared folder id on Google Drive
html_file = './html/index.html'
max_num_img = 5 #Maximum number of image at any moment
frequency = 12 #Upload period in second

while True:
  start_time = time.time()
  #Capture image and blur
  capture_and_blur(blur_degree)
  #Upload image
  insert_file(service,'latest.jpg','my_first_trial',folder_id,'','latest_img.jpg')
  #Check for all existing image online
  img_id_list = print_files_in_folder(service,folder_id)
  if len(img_id_list) > 0:
      html_update(img_id_list[-1])
  #Delete old images
  if len(img_id_list) > max_num_img:
      for img_id in img_id_list[:-max_num_img]:
          print(img_id)
          delete(service,img_id)
  #print('Execution time: {}'.format(time.time()-start_time))
  time.sleep(max(0,frequency-time.time()+start_time))