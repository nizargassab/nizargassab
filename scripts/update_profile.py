"""Render profile widgets from GitHub public repository and contribution data."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json, os, sys, urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'generated'
OUT.mkdir(parents=True, exist_ok=True)
USER = 'nizargassab'
BG, INK, BLUE, GREEN, LINE = '#01102d', '#d5e7ff', '#6eb9f2', '#41c350', '#183252'

def fetch_data():
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        raise RuntimeError('GitHub token is required to refresh the public profile statistics.')
    query = '''query($login:String!) { user(login:$login) {
      login name followers { totalCount } following { totalCount }
      repositories(privacy:PUBLIC,first:100,orderBy:{field:UPDATED_AT,direction:DESC}) {
        totalCount nodes { name description url isFork stargazerCount forkCount primaryLanguage { name color } }
      }
      contributionsCollection {
        totalCommitContributions totalIssueContributions totalPullRequestContributions totalPullRequestReviewContributions
        contributionCalendar { totalContributions weeks { contributionDays { date contributionCount color weekday } } }
      }
    } }'''
    request = urllib.request.Request('https://api.github.com/graphql',
        data=json.dumps({'query':query,'variables':{'login':USER}}).encode(),
        headers={'Authorization':'Bearer '+token,'User-Agent':'nizar-profile-widgets','Content-Type':'application/json'})
    with urllib.request.urlopen(request, timeout=45) as response:
        result = json.load(response)
    if result.get('errors'):
        raise RuntimeError('GitHub could not refresh the statistics: '+str(result['errors']))
    return result['data']['user']

def text(x,y,value,size=16,color=INK,weight=400,anchor='start'):
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>'

def svg(name,width,height,body,title):
    content=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title><rect width="{width}" height="{height}" rx="8" fill="{BG}"/>{body}</svg>'
    (OUT/name).write_text(content,encoding='utf-8')

def render_stats(data):
    repos=data['repositories']['nodes']
    collection=data['contributionsCollection']
    stars=sum(r['stargazerCount'] for r in repos if not r['isFork'])
    calendar=collection['contributionCalendar']
    days=[d for week in calendar['weeks'] for d in week['contributionDays']]
    start,end=days[0]['date'],days[-1]['date']
    body=text(26,38,"Nizar's GitHub stats",24,BLUE,700)
    values=[('Profile contributions',calendar['totalContributions']),('Commits',collection['totalCommitContributions']),('Pull requests',collection['totalPullRequestContributions']),('Issues',collection['totalIssueContributions']),('Code reviews',collection['totalPullRequestReviewContributions'])]
    for i,(label,value) in enumerate(values):
        y=78+i*34
        body+=f'<circle cx="31" cy="{y-5}" r="4" fill="{GREEN}"/>'+text(48,y,label,16)+text(404,y,value,17,GREEN,700,'end')
    body+=text(26,267,f'{start} to {end}',12,BLUE)
    svg('stats.svg',440,290,body,'GitHub contribution statistics for Nizar Gassab')
    body=text(26,38,'Public repositories',24,BLUE,700)
    for i,(label,value) in enumerate([('Repositories',data['repositories']['totalCount']),('Stars received',stars),('Followers',data['followers']['totalCount']),('Following',data['following']['totalCount'])]):
        y=81+i*40
        body+=text(26,y,label,16)+text(404,y,value,20,GREEN,700,'end')
    body+=text(26,267,'Updated '+datetime.now(timezone.utc).strftime('%Y-%m-%d')+' UTC',12,BLUE)
    svg('public-profile.svg',440,290,body,'Public repository and follower counts')
    langs=Counter(r['primaryLanguage']['name'] for r in repos if r['primaryLanguage'] and not r['isFork'])
    colors={r['primaryLanguage']['name']:r['primaryLanguage']['color'] or BLUE for r in repos if r['primaryLanguage']}
    body=text(26,37,'Languages in public repositories',22,BLUE,700)
    total=sum(langs.values()) or 1
    for i,(language,count) in enumerate(langs.most_common(6)):
        y=72+i*39
        body+=text(26,y,language,14)+text(610,y,f'{count} repos',13,INK,400,'end')
        body+=f'<rect x="26" y="{y+8}" width="584" height="7" rx="3" fill="{LINE}"/><rect x="26" y="{y+8}" width="{584*count/total:.1f}" height="7" rx="3" fill="{colors[language]}"/>'
    body+=text(26,330,'Repository primary language; public, non-fork repositories only.',12,BLUE)
    svg('languages.svg',640,352,body,'Primary languages of public non-fork repositories')
    return days,calendar

def render_calendar(calendar):
    weeks=calendar['weeks']
    cell,step,left,top=11,15,32,68
    width=left*2+len(weeks)*step
    palette=['#102446','#164e37','#1c7942','#30a24a','#41c350']
    def level(n):return 0 if n==0 else 1 if n<3 else 2 if n<7 else 3 if n<15 else 4
    rects=[];points=[]
    for wi,week in enumerate(weeks):
        for day in week['contributionDays']:
            x,y=left+wi*step,top+day['weekday']*step
            count=day['contributionCount']
            rects.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{palette[level(count)]}"><title>{day["date"]}: {count} contributions</title></rect>')
            points.append((wi,day['weekday'],count))
    base=text(30,35,'Contribution calendar',22,BLUE,700)+''.join(rects)
    base+=text(30,204,f'{calendar["totalContributions"]} contributions in the last year',13,BLUE)
    svg('calendar.svg',width,227,base,'Actual GitHub contribution calendar')
    route=[]
    for row in range(7):
        columns=range(len(weeks)) if row%2==0 else reversed(range(len(weeks)))
        for col in columns:route.append((left+col*step+cell/2,top+row*step+cell/2))
    route_path='M '+' L '.join(f'{x},{y}' for x,y in route)
    snake=f'<path d="{route_path}" fill="none" stroke="#4aa8ff" stroke-width="10" stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="68 10000"><animate attributeName="stroke-dashoffset" from="0" to="-5700" dur="32s" repeatCount="indefinite"/></path>'
    svg('snake.svg',width,227,base+snake,'Animated snake moving through Nizar’s contribution calendar')
    pacman=f'<g><path d="M0,0 L9,-8 A12,12 0 1,0 9,8 Z" fill="#f7d84a"><animate attributeName="d" values="M0,0 L9,-8 A12,12 0 1,0 9,8 Z;M0,0 L12,-1 A12,12 0 1,0 12,1 Z;M0,0 L9,-8 A12,12 0 1,0 9,8 Z" dur="0.3s" repeatCount="indefinite"/></path><animateMotion path="{route_path}" dur="32s" repeatCount="indefinite" rotate="auto"/></g>'
    svg('pacman.svg',width,227,base+pacman,'Animated Pac-Man moving through Nizar’s contribution calendar')
    # Isometric bars use the exact daily counts rather than decorative random data.
    body=text(30,36,'A year of contributions',22,BLUE,700)
    for wi,row,count in sorted(points,key=lambda p:p[0]+p[1]):
        x=100+wi*12+row*12;y=155+row*7-wi*.55
        h=3+min(count,60)/60*55
        color=palette[level(count)]
        body+=f'<g><title>{count} contributions</title><path d="M{x},{y-h} l10,6 l10,-6 l-10,-6 Z" fill="{color}"/><path d="M{x},{y-h} l10,6 v{h} l-10,-6 Z" fill="{color}" opacity=".65"/><path d="M{x+10},{y-h+6} l10,-6 v{h} l-10,6 Z" fill="{color}" opacity=".85"/></g>'
    body+=text(30,241,'Each column represents one day of GitHub activity.',13,BLUE)
    svg('contributions-3d.svg',width,265,body,'Isometric daily contributions chart')
    sums=[sum(day['contributionCount'] for day in week['contributionDays']) for week in weeks]
    max_count=max(sums) or 1
    coords=[(35+i*(width-70)/(len(sums)-1),190-value*120/max_count) for i,value in enumerate(sums)]
    line='M '+' L '.join(f'{x:.1f},{y:.1f}' for x,y in coords)
    body=text(30,35,'Weekly contribution activity',22,BLUE,700)
    body+=f'<path d="{line} L{width-35},200 L35,200 Z" fill="{GREEN}" opacity=".12"/><path d="{line}" stroke="{GREEN}" fill="none" stroke-width="2.5"/>'
    body+=text(35,230,weeks[0]['contributionDays'][0]['date'],12,BLUE)+text(width-35,230,weeks[-1]['contributionDays'][-1]['date'],12,BLUE,400,'end')
    svg('activity.svg',width,250,body,'Weekly GitHub contribution totals')

def render_projects():
    projects=[
      ('craft-my-lesson','Craft My Lesson','Images into printable classroom activities.','Python / FastAPI / React / TypeScript'),
      ('mezacall','MezaCall','Browser telephony and live call supervision.','React / WebRTC / SIP.js / FreeSWITCH'),
      ('normdesk','NormDesk','CRM workflows and document-based AI.','React / TypeScript / PostgreSQL / Ollama'),
      ('izemx-lab','IZEMX Lab','Team contribution: AI SaaS and back office.','Spring Boot / React / Keycloak'),
      ('syndexpress','SyndExpress','Team contribution: property-management SaaS.','Spring Boot / React / React Native'),
      ('health-track','Health Track','Team contribution: medical follow-up platform.','Angular / Spring Cloud / JWT / Docker')]
    for slug,title,description,stack in projects:
        body=f'<rect x=".5" y=".5" width="439" height="134" rx="8" fill="none" stroke="{LINE}"/>'
        body+='<path d="M25 22h14v18H25z M25 35h14" fill="none" stroke="'+BLUE+'" stroke-width="1.7"/>'
        body+=text(49,38,title,19,BLUE,700)+text(25,72,description,13)+text(25,108,stack,12,GREEN)
        svg('project-'+slug+'.svg',440,135,body,title+' project showcase')

if __name__=='__main__':
    data=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')) if len(sys.argv)>1 else fetch_data()
    if data['login']!=USER:raise RuntimeError('Unexpected GitHub account')
    days,calendar=render_stats(data)
    render_calendar(calendar)
    render_projects()
    print(f'Rendered {len(list(OUT.glob("*.svg")))} widgets using {len(days)} days of GitHub activity.')
