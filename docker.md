# Docker

- Built on Python 3.11.6 image
- Create an admin at stratup using environement variables
- Publish your domain (for CSRF)
- Update the Secret Key
- Replace sqlite location to a data directory that can be mapped

## Build

'''
docker build -t horilla .
'''

## Run

'''
docker run -p 8000:8000 -v ./data:/data -v ./data:/horilla/media -e FIRST_NAME=System -e LAST_NAME=Admin -e USERNAME=admin -e PASSWORD=thisisapassword -e EMAIL=info@yourdomain.com -e PHONE=8885556666 -e SECRET_KEY=MyVerySecretSecretShouldBeWrittenHere -e URL=https://hr.yourdomain.com horilla
'''
