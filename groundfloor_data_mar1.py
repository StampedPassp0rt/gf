'''Getting loan data from Groundfloor. Curious about % of loans that did well by grade.'''

#libraries
import requests
import pandas as pd
import numpy as np
import re
import yaml
import json
from bs4 import BeautifulSoup

#get all the loan URLs from "funded page"
r_funded = requests.get('https://www.groundfloor.us/education/funded')
r_funded.status_code == requests.codes.ok

#Get content
r_funded.content
#Need to parse with BeautifulSoup
link_soup = BeautifulSoup(r_funded.content, 'lxml')

#Getting the links for all funded loans
link_list = []
for listing in link_soup.find('section', {'class':'container-wrapper odd'}).find_all('a'):
    print str(listing.get('href'))
    link_list.append(str(listing.get('href')))

#192 Loans as of Feb 28, 2017
#193 loans funded as of Mar 1, 2017
#193 loans funded as of Mar 3, 2017
len(link_list)


#find all grades for funded loans - interesting - they say 144 loans funded, but page has 169.
#Looks like part of the website are not fully updated.
#Keeping this relatively basic. Each detail about loan is a Pandas series, so scraping like this.
#For the row where it has all the numerical terms, I could scrape the row and then figure out how to split,
#but I am doing it with each numerical term as a column/series.
addresses = []
grades = []
rates = []
term = []
loantovalue = []
temp_list_details = []

for row in link_soup.find_all('div', {'class': 'row promoted_offers'}):
    for address in row.find_all('div', {'class': 'title'}):
        addresses.append(str(address.get_text()))
    for grade in row.find_all('div', {'class': 'triangle'}):
        grades.append(str(grade.get_text()))
    for details in row.find_all('div', {'class': 'number'}):
        temp_list_details.append(float(details.get_text().strip()))

#Get the information from the details into the three series: rates, term, LTV.
rates = temp_list_details[::3]
term = temp_list_details[1::3]
loantovalue = temp_list_details[2::3]

#Let's put together the current information into a dataframe of loan information and
#links.

loan_funded_master = pd.DataFrame({'address':addresses, 'grade':grades, 'int_rate':rates, 'term_mo': term, 'ltv': loantovalue, 'link_loan_details': link_list})


#obtaining additional loan information
'''
base url is https://www.groundfloor.us
information that could be useful:

    1) Loan Amount;
    2) Full address;
    3) Purpose;
    4) Loan Position;
    5) # of investors - loan updates seems like it would have this information;
    6) When funded;
    7) Who borrowed - wonder if there is a pattern that'll emerge.
    8) Repaid on
    9) Is there GIS data? Could I link to MRIS or another system to understand what houses are
        selling and the time on market in that neighborhood? Or would that be captured in grade?
    10) I know I have zip code, so I could probably blend in for the prior year:
        1) Average HH income for area?
        2) Unemployment rate for area?
        3) If I could get days a house is on market for that area? MRIS?
        4) Change in population for area?
        5) What real estate trends for the area?
        6) 30 year Mortgage demand in that area?
        7) Prior three year's housing price growth in that area?
        8) Change in income for that area over a year? Three years?
        9) Housing supply growth? How?
    Might want to scrub out loans that were funded and repaid in one month. Seems shady. Especially if no loan updates.

Focus on Items 1-8 first. 9 and 10 will be interesting after I have all the data.

'''

#function to get loan info.
#list of links that did not process properly.

''' Have to fix null for maturity date.
And the ones with a null funded date will need to be manually fixed.
Also need to figure out how to fix that
set value bug where if a column is one type of value, it does not allow different values to be set.'''
faulty_list = []

def get_loan_details(page_soup, row_num):
        #iterating through panel class for data
        for panel in page_soup.find_all('article', class_ = 'panel'):
            #get the full address
            if page_soup.find('h2').get_text().split('\n')[4]=='':
                loan_funded_master.set_value(row_num, 'full_address', page_soup.find('h2').get_text().split('\n')[3])
                #get the zip code only
                loan_funded_master.set_value(row_num, 'zipcode', page_soup.find('h2').get_text().split('\n')[3].split()[-1])
            else:
                loan_funded_master.set_value(row_num, 'full_address', page_soup.find('h2').get_text().split('\n')[4])
                #get the zip code only
                loan_funded_master.set_value(row_num, 'zipcode', page_soup.find('h2').get_text().split('\n')[4].split()[-1])
            #get the borrower details
            borrower_list = []
            for borrower_detail in page_soup.find('div', class_ = 'row profile-info').stripped_strings:
                borrower_list.append(borrower_detail)
            #borrower company
            loan_funded_master.set_value(row_num, 'borrower_company', borrower_list[1])
            #borrower principal
            loan_funded_master.set_value(row_num, 'borrower_principal', borrower_list[2])

            #Loan Purpose list
            loan_purpose_list = []
            for detail in page_soup.find_all('div', class_ = 'white-box'):
                loan_purpose_list.append(detail.get_text().strip('\n'))
            #loan purpose
            loan_funded_master.set_value(row_num, 'purpose', loan_purpose_list[0])
            #loan Position
            loan_funded_master.set_value(row_num, 'loan_position', loan_purpose_list[1])
            #loan Amount
            loan_funded_master.set_value(row_num, 'loan_amount', float(loan_purpose_list[2].replace('$','').replace(',','')))
            #loan status
            loan_funded_master.set_value(row_num, 'loan_status', loan_purpose_list[3])
            #loan funded date
            if len(loan_purpose_list) == 8:
                try:
                    if not loan_purpose_list[5]:
                        funded_date = pd.to_datetime(loan_purpose_list[4], infer_datetime_format = True)
                    else:
                        funded_date = pd.to_datetime(loan_purpose_list[5], infer_datetime_format= True)
                except ValueError:
                    funded_date = None
                loan_funded_master.set_value(row_num, 'funded_date', funded_date)
                loan_funded_master.set_value(row_num, 'inception_date', loan_purpose_list[4])
                loan_funded_master.set_value(row_num, 'repaid_date', loan_purpose_list[6])
                loan_funded_master.set_value(row_num, 'maturity_date', loan_purpose_list[7])
            elif len(loan_purpose_list) != 8:
                loan_funded_master.set_value(row_num, 'funded_date', None)
                loan_funded_master.set_value(row_num, 'inception_date', None)
                loan_funded_master.set_value(row_num, 'repaid_date', None)
                loan_funded_master.set_value(row_num, 'maturity_date', None)
            else:
                loan_funded_master.set_value(row_num, 'funded_date', loan_purpose_list[5])
                loan_funded_master.set_value(row_num, 'inception_date', loan_purpose_list[4])
                loan_funded_master.set_value(row_num, 'repaid_date', loan_purpose_list[6])
                loan_funded_master.set_value(row_num, 'maturity_date', loan_purpose_list[7])
            loan_blackbox = []
            investors = None
            investors_search = re.compile('investors|lenders')
            for info in page_soup.find_all('div', class_ = 'black-box'):
                loan_blackbox.append(info.get_text())
            #Checking for investor info in the blackbox, and not equal to zero.
            if int(loan_blackbox[4]) != 0:
                investors = int(loan_blackbox[4])
            #Checking updates if investors = 0 in blackbox.
            elif page_soup.find('div', class_ = 'updates') != None:
                for info in page_soup.find('div', class_ = 'updates').stripped_strings:
                    if info != None:
                        if investors_search.search(info) != None:
                            investors = int(info.split()[-2])
                        else:
                            investors = 0
                    else:
                        investors = 0
            else:
                #updates is not there.
                investors = 0
            loan_funded_master.set_value(row_num, 'investors', investors)


def get_fin_overview(page_soup, row_num):
            #Get Financial Overview data
            financial_overview = []
            for detail in page_soup.find_all('article', class_ = 'panel financial_overview'):
                financial_overview.append(detail.get_text().strip('\n'))
            financial_overview_unfiltered_list = financial_overview[0].split('\n')
            financial_overview_list = list(filter(None, financial_overview_unfiltered_list))
            after_repair_value = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'After Repair Value (ARV)']
            #after repair value
            arv = int(after_repair_value[0].strip('$').replace(',', ''))
            loan_funded_master.set_value(row_num, 'after_repair_value', arv)

            #total project costs
            total_project_costs = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'Total Project Costs']
            total_project_costs_final = int(total_project_costs[0].strip('$').replace(',', ''))
            loan_funded_master.set_value(row_num, 'total_project_costs', total_project_costs_final)

            #skin in game
            sig = [financial_overview_list[i+2] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'GROUNDFLOOR']
            if sig[0] != '0%':
                skin_in_game = int(sig[0].strip('$').replace(',', ''))
            else:
                skin_in_game = 0
            loan_funded_master.set_value(row_num, 'skin_in_game', skin_in_game)

            #Purchase Price of Asset - what borrower bought asset at before renovation,etc.
            pp = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'Purchase Price']
            purchase_price = int(pp[0].strip('$').replace(',', ''))
            loan_funded_master.set_value(row_num, 'init_purchase_price', purchase_price)

            #Purchase Date - when asset was bought by borrower - usually before the loan was requested from Groundfloor
            purch_date = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'Purchase Date']
            if re.search('^TBD', purch_date[0]):
                purchase_date = None
            else:
                purchase_date = pd.to_datetime(purch_date[0], infer_datetime_format = True)
            loan_funded_master.set_value(row_num, 'init_purchase_date', purchase_date)

            #Loan to ARV % (should be the LTV value, but here for double checking)
            loan_arv = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'Loan To ARV']
            loan_to_arv_decimal = float(loan_arv[0].replace('%', ''))/100
            loan_funded_master.set_value(row_num, 'loan_to_arv_decimal', loan_to_arv_decimal)

            #Loan to Total Project Cost - Essentially how much of the project is financed by loan.
            #Interesting to know b/c ARV is speculative until actually sold at which point loan is covered.
            loan_tpc = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'Loan To Total Project Cost']
            loan_tpc_decimal = float(loan_tpc[0].replace('%', ''))/100
            loan_funded_master.set_value(row_num, 'loan_tpc_decimal', loan_tpc_decimal)

def get_grade_factors(page_soup, row_num):
            #Grade Factors for Loan Grade
            grade_factors = []
            for detail in page_soup.find_all('div', class_ = 'grade_factors content append-bottom-1'):
                grade_factors.append(detail.get_text().strip('\n'))
            grade_factors_list = filter(None, grade_factors[0].split('\n'))
            #Loan To ARV Strength - Stronger this is, more likely the loan grade is high (guessing) and same with other factors
            loan_arv_strength = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Loan', grade_factors_list[i])][0])/10
            loan_funded_master.set_value(row_num, 'loan_arv_strength', loan_arv_strength)

            #Skin in Game Strength
            skin_in_game_strength = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Skin', grade_factors_list[i])][0])/10
            loan_funded_master.set_value(row_num, 'skin_in_game_strength', skin_in_game_strength)

            #Location Strength
            location_strength = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Location', grade_factors_list[i])][0])/8
            loan_funded_master.set_value(row_num, 'location_strength', location_strength)

            #Borrower Experience Strength
            borrower_exp_strength = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Borrower Experience', grade_factors_list[i])][0])/5
            loan_funded_master.set_value(row_num, 'borrower_exp_strength', borrower_exp_strength)

            #Borrower Commitment Strength - 0 means part time, 1 means full time.
            borrower_com_strength = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Borrower Commitment', grade_factors_list[i])][0])
            loan_funded_master.set_value(row_num, 'borrower_commitment_strength', borrower_com_strength)

            #Val Report Quality Strength - A 4 out of 4 is best
            quality_val_report = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Quality', grade_factors_list[i])][0])/4
            loan_funded_master.set_value(row_num, 'quality_val_report', quality_val_report)

            #Valuation Report
            val_report = []
            for detail in page_soup.find_all('div', class_ = 'btn-open-option btn-selected-option'):
                val_report.append(detail.get_text().strip('\n'))
            val_report_list = filter(None, val_report[0].split('\n'))
            loan_funded_master.set_value(row_num, 'val_report_source', val_report_list)

#Getting the full loan details
    #check how I iterate over series and index.
    #else zip the two together and use the tuple in a for loop
    #b/c below is not correct
error_list_loan_details = []
for loan_url, row_number in zip(loan_funded_master['link_loan_details'], loan_funded_master.index):
    try:
        page = requests.get('https://www.groundfloor.us'+loan_url)
        #Check if page was obtained
        if page.status_code!=requests.codes.ok:
            faulty_list.append(loan_url)
        else:
            page_soup = BeautifulSoup(page.content, 'lxml')
            get_loan_details(page_soup, row_number)
    except (AttributeError, IndexError, ValueError) as e:
        error_list_loan_details.append((row_number, e))
        print "Error at %i row" % row_number

#Check the error list for loan details
for i in error_list_loan_details:
    print i
    print loan_funded_master.ix[i[0]]


error_list_fin_overview = []
for loan_url, row_number in zip(loan_funded_master['link_loan_details'], loan_funded_master.index):
    try:
        page = requests.get('https://www.groundfloor.us'+loan_url)
        #Check if page was obtained
        if page.status_code!=requests.codes.ok:
            faulty_list.append(loan_url)
        else:
            page_soup = BeautifulSoup(page.content, 'lxml')
            get_fin_overview(page_soup, row_number)
    except (AttributeError, IndexError, ValueError) as e:
        error_list_fin_overview.append((row_number, e))
        print "Error at %i row" % row_number

error_list_grade = []
for loan_url, row_number in zip(loan_funded_master['link_loan_details'], loan_funded_master.index):
    try:
        page = requests.get('https://www.groundfloor.us'+loan_url)
        #Check if page was obtained
        if page.status_code!=requests.codes.ok:
            faulty_list.append(loan_url)
        else:
            page_soup = BeautifulSoup(page.content, 'lxml')
            get_grade_factors(page_soup, row_number)
    except (AttributeError, IndexError, ValueError) as e:
        error_list_grade.append((row_number, e))
        print "Error at %i row" % row_number

for i in error_list_grade:
    if re.search('^list index', str(i[1])):
        print "Probably no problem"
    else:
        print i

for i in error_list_fin_overview:
    if re.search('^list index', str(i[1])):
        print "Probably no problem since these loans appear to not have the ARV sections"
    else:
        print i



#Decimalize the terms not already done so.
decimalize = lambda x: float(x)/100
loan_funded_master['int_rate'] = loan_funded_master['int_rate'].apply(decimalize)
loan_funded_master['ltv'] = loan_funded_master['ltv'].apply(decimalize)

#Check for null timestamps
loan_funded_master[loan_funded_master.funded_date.isnull()]
loan_funded_master[loan_funded_master.maturity_date.isnull()]
#This loan is one of the fishy ones, very short actual period despite 12 month term, and funded/inception data missing. Assume for analysis that it is the same as purchase date.
loan_funded_master.set_value(0, 'funded_date', loan_funded_master.init_purchase_date[0])
loan_funded_master.set_value(0, 'inception_date', loan_funded_master.init_purchase_date[0])

timestamped = lambda x: pd.to_datetime(x, infer_datetime_format = True)
loan_funded_master['funded_date'] = loan_funded_master['funded_date'].apply(timestamped)
loan_funded_master['inception_date'] = loan_funded_master['inception_date'].apply(timestamped)

for i in range(len(loan_funded_master['maturity_date'])):
    if loan_funded_master.maturity_date[i] != 'N/A':
        loan_funded_master.set_value(i, 'maturity_date', pd.to_datetime(loan_funded_master.maturity_date[i], infer_datetime_format = True))

#Have to make sure repaid date is done properly.
#loan_funded_master = loan_funded_master.assign(unformated_repaid_date = loan_funded_master.repaid_date)

for i in range(len(loan_funded_master['repaid_date'])):
    if loan_funded_master.repaid_date[i] != 'Pending':
        loan_funded_master.set_value(i, 'repaid_date', pd.to_datetime(loan_funded_master.repaid_date[i], infer_datetime_format = True))

#Need to look through this carefully - a number of the errors are b/c the ARV data
#not there, but that's b/c Groundfloor doesn't provide for older loans.

#Okay, let's split the loan detail function into three plus parts, so that I can troubleshoot better.

loan_funded_master[loan_funded_master.funded_date.isnull()].index

#Loans that are not funded yet have null funded dates...

loan_funded_master.ix[3]

loan_funded_master.to_csv('groundfloor_fundedloan_database_mar3.csv', sep = ',')



'''Below is code to test out scraping data, which was then made into the above function.

page = requests.get('https://www.groundfloor.us'+loan_funded_master['link_loan_details'][7])
page.status_code == requests.codes.ok

page_soup = BeautifulSoup(page.content, 'lxml')



#1) Double check that Investors number is being obtained. check that I have solved
#for each data element on loan details page.

#2) If I have, then put into the function and fill out data.

#3) And export to CSV. Also consider creating a Postgres database of it.

#4) Calculate default rate by grade. Also see which lenders have lent the most, and repayment times.
#Idea is to find the ones that are too short in repayment time to note as filter out. EDA fun.

#Extra Credit: Figure out how to create a chron job to check daily if new loans are there,
#and then parse them and add to database. Uses SQL too.



#want to extract from the updates the investor number.
#also need logic to check if the number in the first panel for investors is zero, and to use if not zero.
#also need logic to first check if updates is even there, and to extract if there.
#and finally need to extract longitude and latitude from next to last panel.
#extract property photo for hell of it?


investors_search = re.compile('investors|lenders')
for info in page_soup.find('div', class_ = 'updates').stripped_strings:
    if investors_search.search(info) != None:
        print info.split()[-2]



for panel in page_soup.find_all('article', class_ ='panel'):
    #Getting the full address
    loan_funded_master.set_value(1, 'full_address', page_soup.find('h2').get_text().split('\n')[4])
    #Getting zip code only
    loan_funded_master.set_value(1, 'zipcode', page_soup.find('h2').get_text().split('\n')[4].split()[-1])

    #Getting the borrower details
    borrower_list = []
    for borrower_detail in page_soup.find('div', class_ = 'row profile-info').stripped_strings:
        borrower_list.append(borrower_detail)
    #borrower company
    loan_funded_master.set_value(1, 'borrower_company', borrower_list[1])
    #borrower principal
    loan_funded_master.set_value(1, 'borrower_principal', borrower_list[2])

    #Loan Purpose list
    loan_purpose_list = []
    for detail in page_soup.find_all('div', class_ = 'white-box'):
        loan_purpose_list.append(detail.get_text().strip('\n'))
    #loan purpose
    loan_funded_master.set_value(1, 'purpose', loan_purpose_list[0])
    #loan Position
    loan_funded_master.set_value(1, 'loan_position', loan_purpose_list[1])
    #loan Amount
    loan_funded_master.set_value(1, 'loan_amount', float(loan_purpose_list[2].replace('$','').replace(',','')))
    #loan funded date
    if loan_purpose_list[3].split()[-1] == 'Funded' and len(loan_purpose_list) == 8:
        try:
            if not loan_purpose_list[5]:
                funded_date = pd.to_datetime(loan_purpose_list[4], infer_datetime_format = True)
            else:
                funded_date = pd.to_datetime(loan_purpose_list[5], infer_datetime_format= True)
        except ValueError:
            funded_date = 'error'

    #Get Financial Overview data
    financial_overview = []
    for detail in page_soup.find_all('article', class_ = 'panel financial_overview'):
        financial_overview.append(detail.get_text().strip('\n'))
    financial_overview_unfiltered_list = financial_overview[0].split('\n')
    financial_overview_list = list(filter(None, financial_overview_unfiltered_list))
    financial_overview_list
    after_repair_value = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'After Repair Value (ARV)']
    arv = int(after_repair_value[0].strip('$').replace(',', ''))

    total_project_costs = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'Total Project Costs']
    total_project_costs_final = int(total_project_costs[0].strip('$').replace(',', ''))

    sig = [financial_overview_list[i+2] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'GROUNDFLOOR']
    if sig[0] != '0%':
        skin_in_game = int(sig[0].strip('$').replace(',', ''))
    else:
        skin_in_game = 0
    skin_in_game

    pp = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'Purchase Price']
    purchase_price = int(pp[0].strip('$').replace(',', ''))


    purch_date = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'Purchase Date']
    purchase_date = pd.to_datetime(purch_date[0], infer_datetime_format = True)

    loan_arv = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'Loan To ARV']
    loan_to_arv_decimal = float(loan_arv[0].replace('%', ''))/100

    loan_tpc = [financial_overview_list[i+1] for i in range(len(financial_overview_list)) if financial_overview_list[i] == 'Loan To Total Project Cost']
    loan_tpc_decimal = float(loan_tpc[0].replace('%', ''))/100

    #Grade Factors for Loan Grade
    grade_factors = []
    for detail in page_soup.find_all('div', class_ = 'grade_factors content append-bottom-1'):
        grade_factors.append(detail.get_text().strip('\n'))
    grade_factors_list = filter(None, grade_factors[0].split('\n'))
    loan_arv_strength = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Loan', grade_factors_list[i])][0])/10
    skin_in_game_strength = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Skin', grade_factors_list[i])][0])/10
    location_strength = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Location', grade_factors_list[i])][0])/8
    borrower_exp_strength = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Borrower Experience', grade_factors_list[i])][0])/5
    borrower_com_strength = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Borrower Commitment', grade_factors_list[i])][0])/5
    quality_val_report = float([grade_factors_list[i+1] for i in range(len(grade_factors_list)) if re.search('^Quality', grade_factors_list[i])][0])/4

    #Valuation Report
    val_report = []
    for detail in page_soup.find_all('div', class_ = 'btn-open-option btn-selected-option'):
        val_report.append(detail.get_text().strip('\n'))
    val_report_list = filter(None, val_report[0].split('\n'))



    #Check if investors in first panel
    loan_blackbox = []
    investors = []
    for info in page_soup.find_all('div', class_ = 'black-box'):
        loan_blackbox.append(info.get_text())

    if int(loan_blackbox[4]) != 0:
        investors = int(loan_blackbox[4])
    elif page_soup.find('div', class_ = 'updates') != None:
        for info in page_soup.find('div', class_ = 'updates').stripped_strings:
            if info != None:
                if investors_search.search(info) != None:
                    investors = int(info.split()[-2])
                else:
                     investors = 0
            else:
                 investors = 0
    else:
        investors = 0
    loan_funded_master.set_value(1, 'investors', investors)


loan_funded_master.ix[1]
'''
