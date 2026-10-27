"""DPDP-QA: questions written from the text of the DPDP Act, 2023.

Each answerable item has a gold provision, a reference answer and an evidence phrase copied from the
Act. A retrieved chunk is relevant if it contains the phrase, so relevance does not depend on how the
Act is chunked. validate() checks that every phrase occurs in the Act and only inside its gold provision.

The items were written by the project authors with an AI assistant from the statute text. They have
not been reviewed by a lawyer.
"""
from __future__ import annotations

import hashlib
import random

from app.compass.statute import Statute, norm

# type | gold provision | question | reference answer | evidence phrase
EN = """
definition|2(a)|What is the Appellate Tribunal under the DPDP Act?|The Telecom Disputes Settlement and Appellate Tribunal established under section 14 of the TRAI Act, 1997.|Telecom Disputes Settlement
definition|2(b)|What does 'automated' mean in the Act?|Any digital process capable of operating automatically in response to instructions given or otherwise for the purpose of processing data.|capable of operating automatically
definition|2(c)|What is 'the Board'?|The Data Protection Board of India established by the Central Government under section 18.|established by the Central Government under section 18
definition|2(f)|Who is a 'child' under the DPDP Act?|An individual who has not completed the age of eighteen years.|has not completed the age of eighteen years
definition|2(g)|What is a Consent Manager?|A person registered with the Board who acts as a single point of contact to enable a Data Principal to give, manage, review and withdraw her consent through an accessible, transparent and interoperable platform.|single point of contact
definition|2(h)|How does the Act define 'data'?|A representation of information, facts, concepts, opinions or instructions in a manner suitable for communication, interpretation or processing by human beings or by automated means.|representation of information, facts, concepts, opinions or instructions
definition|2(i)|Who is a Data Fiduciary?|Any person who alone or in conjunction with other persons determines the purpose and means of processing of personal data.|determines the purpose and means of processing
definition|2(j)|Who is a Data Principal?|The individual to whom the personal data relates; for a child it includes the parents or lawful guardian, and for a person with disability her lawful guardian acting on her behalf.|the individual to whom the personal data relates
definition|2(k)|Who is a Data Processor?|Any person who processes personal data on behalf of a Data Fiduciary.|processes personal data on behalf of a Data Fiduciary
definition|2(l)|Who is a Data Protection Officer?|An individual appointed by the Significant Data Fiduciary under section 10(2)(a).|an individual appointed by the Significant Data Fiduciary
definition|2(m)|What is a 'digital office'?|An office that adopts an online mechanism in which proceedings, from receipt to disposal, are conducted in online or digital mode.|adopts an online mechanism
definition|2(n)|What is 'digital personal data'?|Personal data in digital form.|means personal data in digital form
definition|2(o)|What does 'gain' mean in the Act?|A gain in property or supply of services, or an opportunity to earn remuneration or gain a financial advantage otherwise than by way of legitimate remuneration.|a gain in property or supply of services
definition|2(p)|What does 'loss' mean in the Act?|A loss in property or interruption in supply of services, or a loss of opportunity to earn remuneration or gain a financial advantage otherwise than by legitimate remuneration.|a loss in property or interruption in supply of services
definition|2(q)|Who is a 'Member'?|A Member of the Board, including the Chairperson.|means a Member of the Board and includes the Chairperson
definition|2(r)|What is a 'notification'?|A notification published in the Official Gazette.|means a notification published in the Official Gazette
definition|2(s)|Who counts as a 'person'?|An individual, a Hindu undivided family, a company, a firm, an association of persons or body of individuals, the State, and every other artificial juristic person.|a Hindu undivided family
definition|2(t)|What is 'personal data'?|Any data about an individual who is identifiable by or in relation to such data.|identifiable by or in relation to such data
definition|2(u)|What is a 'personal data breach'?|Any unauthorised processing of personal data or accidental disclosure, acquisition, sharing, use, alteration, destruction or loss of access to personal data that compromises its confidentiality, integrity or availability.|compromises the confidentiality, integrity or availability
definition|2(v)|What does 'prescribed' mean?|Prescribed by rules made under the Act.|means prescribed by rules made under this Act
definition|2(x)|What does 'processing' cover?|A wholly or partly automated operation or set of operations on digital personal data, including collection, recording, storage, use, sharing, disclosure, erasure and destruction.|wholly or partly automated operation
definition|2(z)|Who is a Significant Data Fiduciary?|Any Data Fiduciary or class of Data Fiduciaries notified by the Central Government under section 10.|as may be notified by the Central Government under section 10
definition|2(za)|What is the 'specified purpose'?|The purpose mentioned in the notice given by the Data Fiduciary to the Data Principal.|the purpose mentioned in the notice given by the Data Fiduciary
definition|2(zb)|How is 'State' defined?|As defined under article 12 of the Constitution.|article 12 of the Constitution
scope|1(2)|When does the Act come into force?|On the date the Central Government appoints by notification; different dates may be appointed for different provisions.|different dates may be appointed for different provisions
scope|3|Does the Act apply to processing that takes place outside India?|Yes, if the processing is in connection with any activity related to offering goods or services to Data Principals within India.|also apply to processing of digital personal data outside the territory of India
scope|3|Does the Act cover data that an individual processes for personal or domestic purposes?|No. The Act does not apply to personal data processed by an individual for any personal or domestic purpose.|for any personal or domestic purpose
scope|3|Does the Act apply to personal data that the Data Principal has herself made public?|No. It does not apply to personal data made or caused to be made publicly available by the Data Principal.|made or caused to be made publicly available
scope|4(1)|On what grounds may personal data be processed?|Only in accordance with the Act and for a lawful purpose, with the Data Principal's consent or for certain legitimate uses.|only in accordance with the provisions of this Act and for a lawful purpose
scope|4(2)|What is a 'lawful purpose'?|Any purpose which is not expressly forbidden by law.|not expressly forbidden by law
scope|38(2)|If the DPDP Act conflicts with another law, which prevails?|The DPDP Act prevails to the extent of the conflict.|shall prevail to the extent of such conflict
scope|38(1)|Does the DPDP Act replace other laws?|No. Its provisions are in addition to and not in derogation of any other law in force.|in addition to and not in derogation of
obligation|5(1)|What must accompany a request for consent?|A notice from the Data Fiduciary stating the personal data and purpose, how to exercise the rights to withdraw consent and to grievance redressal, and how to complain to the Board.|shall be accompanied or preceded by a notice
obligation|5(2)|What must a Data Fiduciary do about consent it obtained before the Act commenced?|Give the Data Principal a notice as soon as reasonably practicable; it may continue processing until she withdraws consent.|as soon as it is reasonably practicable
obligation|5(3)|In which languages must the notice be accessible?|In English or any language specified in the Eighth Schedule to the Constitution.|option to access the contents of the notice
obligation|6(1)|What conditions must valid consent satisfy?|It must be free, specific, informed, unconditional and unambiguous with a clear affirmative action, and limited to the personal data necessary for the specified purpose.|free, specific, informed, unconditional and unambiguous
obligation|6(3)|How must a request for consent be presented?|In clear and plain language, with the option to access it in English or an Eighth Schedule language, and with the contact details of a Data Protection Officer or other authorised person.|in a clear and plain language
obligation|6(6)|What must a Data Fiduciary do once consent is withdrawn?|Within a reasonable time cease, and cause its Data Processors to cease, processing the personal data, unless processing without consent is required or authorised by law.|cease and cause its Data Processors to cease processing
obligation|6(8)|To whom is a Consent Manager accountable?|To the Data Principal, on whose behalf it acts.|shall be accountable to the Data Principal
obligation|6(9)|Must a Consent Manager be registered?|Yes, with the Board, subject to prescribed technical, operational, financial and other conditions.|shall be registered with the Board
obligation|6(10)|Who must prove that consent was given if the question arises in a proceeding?|The Data Fiduciary must prove that a notice was given and consent was obtained in accordance with the Act.|shall be obliged to prove that a notice was given
obligation|8(1)|Is a Data Fiduciary responsible for processing carried out by its Data Processor?|Yes. It is responsible for compliance in respect of any processing undertaken by it or on its behalf by a Data Processor, irrespective of any agreement to the contrary.|irrespective of any agreement to the contrary
obligation|8(2)|On what basis may a Data Fiduciary engage a Data Processor?|Only under a valid contract.|only under a valid contract
obligation|8(3)|When must a Data Fiduciary ensure that personal data is accurate?|When the data is likely to be used to make a decision that affects the Data Principal or to be disclosed to another Data Fiduciary.|ensure its completeness, accuracy and consistency
obligation|8(4)|What measures must a Data Fiduciary implement to observe the Act?|Appropriate technical and organisational measures.|appropriate technical and organisational measures
obligation|8(5)|What security duty does a Data Fiduciary have?|To protect personal data in its possession or control, including data handled by its Data Processor, by taking reasonable security safeguards to prevent personal data breach.|by taking reasonable security safeguards
obligation|8(6)|Whom must a Data Fiduciary inform when a personal data breach occurs?|The Board and each affected Data Principal, in the prescribed form and manner.|give the Board and each affected Data Principal
obligation|8(7)|When must a Data Fiduciary erase personal data?|When the Data Principal withdraws consent or as soon as it is reasonable to assume the specified purpose is no longer being served, whichever is earlier, unless retention is necessary to comply with a law.|as soon as it is reasonable to assume that the specified purpose is no longer being served
obligation|8(8)|When is the specified purpose deemed to be no longer served?|When the Data Principal neither approaches the Data Fiduciary for the purpose nor exercises her rights for the prescribed time period.|shall be deemed to no longer be served
obligation|8(9)|What contact information must a Data Fiduciary publish?|The business contact information of a Data Protection Officer, if applicable, or of a person who can answer the Data Principal's questions about processing.|who is able to answer on behalf of the Data Fiduciary
obligation|8(10)|Must a Data Fiduciary have a grievance redressal mechanism?|Yes. It must establish an effective mechanism to redress the grievances of Data Principals.|establish an effective mechanism to redress the grievances
obligation|9(1)|What consent is needed before processing a child's personal data?|Verifiable consent of the parent or lawful guardian.|obtain verifiable consent of the parent
obligation|9(2)|May a Data Fiduciary process data in a way that could harm a child?|No. It must not undertake processing likely to cause any detrimental effect on the well-being of a child.|detrimental effect on the well-being of a child
obligation|9(3)|Can a Data Fiduciary track children's behaviour?|No. Tracking or behavioural monitoring of children and targeted advertising directed at children are prohibited.|tracking or behavioural monitoring of children
obligation|10(2)|What must a Significant Data Fiduciary do in addition to ordinary duties?|Appoint a Data Protection Officer based in India, appoint an independent data auditor, and undertake periodic Data Protection Impact Assessments and audits.|appoint an independent data auditor
obligation|10(2)|Where must the Data Protection Officer of a Significant Data Fiduciary be based?|In India.|be based in India
obligation|12(2)|What must a Data Fiduciary do when it receives a correction request?|Correct inaccurate or misleading data, complete incomplete data and update the data.|correct the inaccurate or misleading personal data
obligation|12(3)|Must a Data Fiduciary erase personal data when the Data Principal asks?|Yes, unless retention is necessary for the specified purpose or for compliance with a law.|upon receipt of such a request, the Data Fiduciary shall erase her personal data
obligation|13(2)|Does the Act require Data Fiduciaries to respond to grievances?|Yes, within the period that may be prescribed.|respond to any grievances referred to in sub-section (1)
obligation|15|What duties does a Data Principal have?|To comply with applicable laws, not impersonate another person, not suppress material information, not register false or frivolous grievances, and furnish only verifiably authentic information.|not to impersonate another person
obligation|15|May a Data Principal register a frivolous complaint with the Board?|No. She has a duty not to register a false or frivolous grievance or complaint.|not to register a false or frivolous grievance
obligation|37(2)|Must an intermediary obey a blocking direction of the Central Government?|Yes. Every intermediary who receives such a direction is bound to comply.|Every intermediary who receives a direction
right|6(4)|Can a Data Principal withdraw her consent?|Yes, at any time, and withdrawing must be as easy as giving consent.|right to withdraw her consent at any time
right|6(7)|Through whom may a Data Principal manage her consent?|Through a Consent Manager.|withdraw her consent to the Data Fiduciary through a Consent Manager
right|11(1)|What information can a Data Principal obtain about the processing of her data?|A summary of the personal data being processed and the processing activities, and the identities of the other Data Fiduciaries and Data Processors with whom it has been shared.|a summary of personal data which is being processed
right|11(1)|Can a Data Principal find out with whom her data has been shared?|Yes. She can obtain the identities of all other Data Fiduciaries and Data Processors with whom it was shared, with a description of the data shared.|identities of all other Data Fiduciaries and Data Processors
right|11(2)|Is there an exception to the right to know with whom data was shared?|Yes: sharing with another Data Fiduciary authorised by law, on a written request, for prevention, detection or investigation of offences or cyber incidents.|prevention or detection or investigation of offences or cyber incidents
right|12(1)|What rights does a Data Principal have over inaccurate personal data?|The right to correction, completion, updating and erasure of her personal data.|right to correction, completion, updating and erasure
right|13(1)|Does a Data Principal have a right to grievance redressal?|Yes, to readily available means of grievance redressal provided by the Data Fiduciary or Consent Manager.|readily available means of grievance redressal
right|13(3)|Can a Data Principal approach the Board directly with a grievance?|No. She must first exhaust the opportunity of redressing her grievance with the Data Fiduciary or Consent Manager.|exhaust the opportunity of redressing her grievance
right|14(1)|Can a Data Principal nominate someone to exercise her rights?|Yes. She may nominate another individual to exercise her rights in the event of her death or incapacity.|in the event of death or incapacity of the Data Principal
right|14(2)|What does 'incapacity' mean for the purposes of nomination?|Inability to exercise rights due to unsoundness of mind or infirmity of body.|unsoundness of mind or infirmity of body
right|29(1)|Can a person appeal against an order of the Board?|Yes, to the Appellate Tribunal.|may prefer an appeal before the Appellate Tribunal
right|6(5)|Does withdrawing consent make earlier processing unlawful?|No. Withdrawal does not affect the legality of processing done before it, and its consequences are borne by the Data Principal.|shall not affect the legality of processing
right|6(2)|Is a part of consent that infringes the Act valid?|No. It is invalid to the extent of the infringement.|invalid to the extent of such infringement
right|27(1)|Can a Data Principal complain to the Board about a Consent Manager?|Yes. The Board inquires into a breach by a Consent Manager of its obligations and may impose a penalty.|breach in observance by a Consent Manager of its obligations
exemption|17(1)|Do the consent obligations apply when processing is necessary to enforce a legal right or claim?|No. Chapter II (except section 8(1) and 8(5)), Chapter III and section 16 do not apply.|necessary for enforcing any legal right or claim
exemption|17(1)|Are courts and tribunals exempt from Chapter II when performing their functions?|Yes, where processing is necessary for a judicial, quasi-judicial, regulatory or supervisory function.|judicial or quasi-judicial or regulatory or supervisory function
exemption|17(1)|Is processing for the investigation of offences exempt from the consent obligations?|Yes. Processing in the interest of prevention, detection, investigation or prosecution of any offence is exempt from Chapter II (except section 8(1) and 8(5)), Chapter III and section 16.|prevention, detection, investigation or prosecution of any offence
exemption|17(1)|Does Chapter II apply to data of people outside India processed in India under a foreign contract?|No.|pursuant to any contract entered into with any person outside the territory of India
exemption|17(1)|Is processing needed for a court-approved merger exempt?|Yes.|scheme of compromise or arrangement or merger or amalgamation
exemption|17(1)|Is processing to assess the assets of a loan defaulter exempt?|Yes, subject to the disclosure provisions of other laws.|defaulted in payment due on account of a loan or advance
exemption|17(2)|Is processing for research, archiving or statistical purposes exempt from the Act?|Yes, if the data is not used to take any decision specific to a Data Principal and prescribed standards are followed.|necessary for research, archiving or statistical purposes
exemption|17(2)|Can instrumentalities of the State be exempted from the Act for national security?|Yes, as the Central Government may notify, in the interests of sovereignty, security of the State, friendly relations with foreign States or public order.|friendly relations with foreign States
exemption|17(3)|Can startups be exempted from some provisions?|Yes. The Central Government may notify Data Fiduciaries, including startups, to whom section 5, sections 8(3) and 8(7), and sections 10 and 11 do not apply.|including startups
exemption|17(3)|How is a 'startup' defined for the exemption?|A private limited company, partnership firm or limited liability partnership incorporated in India and recognised as a startup under the notified criteria.|a private limited company or a partnership firm or a limited liability partnership
exemption|17(4)|Do the erasure duties apply to processing by the State?|No. Sections 8(7) and 12(3) do not apply to processing by the State or its instrumentalities.|In respect of processing by the State or any instrumentality of the State
exemption|17(5)|Can the Government exempt Data Fiduciaries for a period after commencement?|Yes, by notification within five years of commencement, for a specified period.|before expiry of five years from the date of commencement
exemption|9(4)|Can some Data Fiduciaries be exempted from the parental consent requirement?|Yes, for classes of Data Fiduciaries or purposes, and subject to conditions, as may be prescribed.|shall not be applicable to processing of personal data of a child
exemption|9(5)|Can the age threshold for the children's obligations be relaxed?|Yes. If processing is verifiably safe, the Central Government may notify an age above which the Data Fiduciary is exempt.|verifiably safe
procedure|18(1)|What body does the Act establish?|The Data Protection Board of India.|a Board to be called the Data Protection Board of India
procedure|18(2)|What is the legal status of the Board?|A body corporate with perpetual succession and a common seal, which can hold property, contract, sue and be sued.|perpetual succession and a common seal
procedure|18(3)|Where is the headquarters of the Board?|At the place the Central Government notifies.|headquarters of the Board
procedure|19(1)|Who makes up the Board?|A Chairperson and such number of other Members as the Central Government notifies.|shall consist of a Chairperson
procedure|19(3)|What qualities must Board Members have?|Ability, integrity and standing, with special knowledge or practical experience in fields such as data governance, consumer protection, dispute resolution, ICT, digital economy or law.|a person of ability, integrity and standing
procedure|19(3)|Must the Board include a legal expert?|Yes, at least one Member must be an expert in the field of law.|at least one among them shall be an expert in the field of law
procedure|20(2)|What is the term of office of Board Members?|Two years, and they are eligible for re-appointment.|hold office for a term of two years
procedure|20(1)|Can a Member's salary be reduced after appointment?|No. Terms of service cannot be varied to their disadvantage after appointment.|shall not be varied to their disadvantage
procedure|21(1)|What disqualifies a person from being a Member of the Board?|Insolvency, conviction for an offence involving moral turpitude, incapacity, a prejudicial financial interest, or abuse of position.|adjudged as an insolvent
procedure|21(2)|Can a Member be removed without a hearing?|No. A Member cannot be removed unless given an opportunity of being heard.|shall not be removed from her office
procedure|22(1)|When does a Member's resignation take effect?|When the Central Government permits, or after three months from receipt of the notice, or when a successor enters office, or at the end of the term, whichever is earliest.|upon expiry of a period of three months
procedure|22(3)|Can a former Member take up employment immediately after leaving?|Not for one year without the previous approval of the Central Government.|for a period of one year from the date on which they cease to hold such office
procedure|23(2)|Does a vacancy in the Board invalidate its proceedings?|No.|any vacancy in or any defect in the constitution of the Board
procedure|23(3)|Who acts when the Chairperson is unable to discharge her functions?|The senior-most Member.|the senior-most Member shall discharge the functions
procedure|24|Can the Board appoint its own officers and employees?|Yes, with the previous approval of the Central Government.|appoint such officers and employees as it may deem necessary
procedure|25|Are the Members of the Board public servants?|Yes, they are deemed to be public servants within the meaning of section 21 of the Indian Penal Code.|deemed, when acting or purporting to act
procedure|26|What powers does the Chairperson have?|General superintendence and direction of administrative matters, authorising officers to scrutinise intimations and complaints, and allocating proceedings among Members.|general superintendence and giving direction
procedure|27(1)|What can the Board do on receiving intimation of a personal data breach?|Direct urgent remedial or mitigation measures, inquire into the breach and impose a penalty.|direct any urgent remedial or mitigation measures
procedure|27(2)|Can the Board issue directions to a person?|Yes, after giving an opportunity of being heard and recording reasons in writing; the person is bound to comply.|issue such directions as it may consider necessary
procedure|27(3)|Can the Board change a direction it has issued?|Yes. It may modify, suspend, withdraw or cancel a direction on a representation or a reference.|modify, suspend, withdraw or cancel such direction
procedure|28(1)|How is the Board meant to function?|As an independent body and, as far as practicable, as a digital office that is digital by design.|shall function as an independent body
procedure|28(3)|What must the Board decide before starting an inquiry?|Whether there are sufficient grounds to proceed with an inquiry.|determine whether there are sufficient grounds to proceed with an inquiry
procedure|28(6)|What principles govern an inquiry by the Board?|The principles of natural justice; the Board must record reasons for its actions.|following the principles of natural justice
procedure|28(7)|What powers does the Board have during an inquiry?|The powers of a civil court for summoning persons, examining on oath, receiving evidence and inspecting documents.|summoning and enforcing the attendance of any person
procedure|28(8)|Can the Board seize a company's equipment during an inquiry?|No. It must not prevent access to premises or take into custody equipment in a way that adversely affects day-to-day functioning.|take into custody any equipment
procedure|28(10)|Can the Board issue interim orders?|Yes, during an inquiry, for reasons recorded in writing and after giving an opportunity of being heard.|issue interim orders
procedure|28(12)|What can the Board do about a false or frivolous complaint?|Issue a warning or impose costs on the complainant.|issue a warning or impose costs on the complainant
procedure|29(2)|What is the time limit for filing an appeal against an order of the Board?|Sixty days from the date of receipt of the order or direction.|within a period of sixty days
procedure|29(6)|How quickly should the Appellate Tribunal dispose of an appeal?|As expeditiously as possible, endeavouring to dispose of it within six months.|dispose of the appeal finally within six months
procedure|31|Can the Board refer a complaint to mediation?|Yes, if it is of the opinion that the complaint may be resolved by mediation.|may be resolved by mediation
penalty|Schedule|What is the maximum penalty for failing to take reasonable security safeguards?|A penalty that may extend to two hundred and fifty crore rupees.|two hundred and fifty crore rupees
penalty|Schedule|What is the penalty for not giving notice of a personal data breach to the Board or affected Data Principals?|A penalty that may extend to two hundred crore rupees.|notice of a personal data breach under sub-section (6) of section 8
penalty|Schedule|What is the maximum penalty for breaching the obligations relating to children?|A penalty that may extend to two hundred crore rupees.|additional obligations in relation to children
penalty|Schedule|What penalty can a Significant Data Fiduciary face for breaching its additional obligations?|A penalty that may extend to one hundred and fifty crore rupees.|one hundred and fifty crore rupees
penalty|Schedule|Can a Data Principal be penalised for breaching her duties, and by how much?|Yes, by a penalty that may extend to ten thousand rupees.|ten thousand rupees
penalty|Schedule|What is the penalty for breach of a provision that the Schedule does not list specifically?|A penalty that may extend to fifty crore rupees.|extend to fifty crore rupees
penalty|Schedule|What is the penalty for breaching a voluntary undertaking?|Up to the extent applicable for the breach in respect of which the proceedings were instituted.|Breach of any term of voluntary undertaking
penalty|33(1)|When may the Board impose a monetary penalty?|When, on conclusion of an inquiry, it determines that a breach is significant, after giving the person an opportunity of being heard.|impose such monetary penalty specified in the Schedule
penalty|33(2)|What factors does the Board consider when fixing the amount of a penalty?|The nature, gravity and duration of the breach, the type of personal data affected, repetition, gain or loss avoided, mitigation, proportionality and the likely impact on the person.|the nature, gravity and duration of the breach
penalty|33(2)|Does mitigation by the offender affect the amount of the penalty?|Yes. The Board considers whether the person acted to mitigate the effects of the breach, and how timely and effective that action was.|took any action to mitigate the effects and consequences of the breach
penalty|34|Where do sums realised as penalties go?|They are credited to the Consolidated Fund of India.|credited to the Consolidated Fund of India
penalty|42(1)|Can the Central Government increase the penalties in the Schedule?|Yes, by notification, but not to more than twice the amount originally specified.|more than twice of what was specified
scenario|5(1)|A bank asks a customer for personal data for video KYC through its app. What must accompany the request?|A notice describing the personal data and the purpose of its processing.|live, video-based customer identification process
scenario|6(1)|A telemedicine app asks for consent to provide telemedicine services and to access the phone contact list. What is the consent limited to?|To processing for telemedicine services, because the contact list is not necessary for that purpose.|telemedicine
scenario|6(2)|An insurer's consent form includes a waiver of the right to complain to the Board. Is that part valid?|No, that part of the consent is invalid.|waiving her right to file a complaint
scenario|6(5)|A shopper withdraws consent after paying for an order. Can the platform stop processing that order?|No. It may stop enabling new orders but may not stop processing for supply of the goods already ordered and paid for.|goods already ordered and paid for
scenario|6(6)|A telecom customer opts to receive bills only in the app. What must the provider do about emailing bills through its processor?|It must itself cease, and cause its Data Processor to cease, processing her data for emailing bills.|emailing telephone bills
scenario|7(a)|A customer gives her mobile number to a pharmacy to receive a payment receipt by message. May the pharmacy use it for that?|Yes. It is a legitimate use: she voluntarily provided the data for that specified purpose.|a pharmacy
scenario|7(a)|A person tells a real estate broker that she no longer needs help finding a flat. What must the broker do?|Cease processing her personal data.|real estate broker
scenario|7(b)|A woman enrols for a government maternity benefit programme. Can the Government use her data to check eligibility for other benefits?|Yes, to determine her eligibility for any other prescribed benefit.|maternity benefits programme
scenario|7(f)|Can personal data be processed without consent in a medical emergency?|Yes, for responding to a medical emergency involving a threat to life or an immediate threat to health.|responding to a medical emergency
scenario|7(g)|Can health data be processed without consent during an epidemic?|Yes, for taking measures to provide medical treatment or health services during an epidemic or other threat to public health.|during an epidemic, outbreak of disease
scenario|7(h)|Can personal data be processed without consent to assist people during a flood or similar disaster?|Yes, for measures to ensure safety or provide assistance during any disaster or breakdown of public order.|during any disaster, or any breakdown of public order
scenario|7(i)|Can an employer process employee data to prevent corporate espionage?|Yes, for purposes of employment or safeguarding the employer from loss or liability.|prevention of corporate espionage
scenario|7(e)|Can a company process personal data to comply with a court order?|Yes, for compliance with any judgment, decree or order issued under a law in force in India.|compliance with any judgment or decree or order
scenario|8(7)|A person sells her used car through an online marketplace and the sale is completed. May the marketplace keep her data?|No. The purpose is served, so it shall no longer retain her personal data.|selling her used car
scenario|8(7)|A customer closes her bank account, and banking law requires identity records to be kept for ten years. Must the bank erase her data now?|No. Retention is necessary for compliance with law, so the bank retains the data for that period.|ten years beyond closing of accounts
scenario|17(1)|A borrower defaults on a loan instalment. Can the bank process her data to ascertain her assets and liabilities?|Yes.|ascertaining her financial information and assets and liabilities
scenario|3|A blogger posts her own personal details publicly on social media. Does the Act apply to that data?|No.|while blogging her views
scenario|5(2)|An e-commerce site obtained consent before the Act began. What must it do once the Act commences?|As soon as practicable, give the user information describing the personal data and the purpose of processing, for example by email or in-app notification.|before the commencement of this Act
lookup|8(5)|What does section 8(5) of the DPDP Act require?|A Data Fiduciary must protect personal data in its possession or under its control by taking reasonable security safeguards to prevent personal data breach.|protect personal data in its possession or under its control
lookup|9(3)|What does section 9(3) prohibit?|Tracking or behavioural monitoring of children and targeted advertising directed at children.|targeted advertising directed at children
lookup|16(1)|What does section 16(1) say about transferring personal data outside India?|The Central Government may, by notification, restrict transfer of personal data to such countries or territories outside India as it notifies.|restrict the transfer of personal data
lookup|16(2)|What is the effect of section 16(2)?|Section 16 does not restrict any law that provides a higher degree of protection for, or restriction on, transfer of personal data outside India.|higher degree of protection
lookup|35|What protection does section 35 give?|No suit or legal proceeding lies against the Central Government, the Board or its Members and staff for anything done in good faith under the Act.|done or intended to be done in good faith
lookup|36|What power does section 36 give the Central Government?|To require the Board and any Data Fiduciary or intermediary to furnish such information as it may call for.|furnish such information as it may call for
lookup|39|What does section 39 say about civil courts?|No civil court has jurisdiction over matters for which the Board is empowered, and no injunction may be granted against action taken under the Act.|No civil court shall have the jurisdiction
lookup|40(1)|What does section 40(1) empower the Central Government to do?|To make rules by notification, subject to previous publication, to carry out the purposes of the Act.|subject to the condition of previous publication
lookup|41|What does section 41 require for rules made under the Act?|Every rule must be laid before each House of Parliament while in session for a total period of thirty days.|for a total period of thirty days
lookup|43(2)|What time limit does section 43(2) set for orders to remove difficulties?|No such order may be made after three years from the commencement of the Act.|after the expiry of three years
lookup|32(1)|What does section 32(1) allow the Board to accept?|A voluntary undertaking from any person at any stage of a proceeding under section 28.|accept a voluntary undertaking
lookup|30(1)|How are orders of the Appellate Tribunal enforced under section 30(1)?|They are executable by the Tribunal as a decree of a civil court.|executable by it as a decree of civil court
"""

# Questions the Act cannot answer: details left to rules or absent from the Act, and out-of-domain requests.
UNANSWERABLE = [
    ("unanswerable_rules", "Within how many hours must a personal data breach be reported to the Board?"),
    ("unanswerable_rules", "What is the registration fee for a Consent Manager?"),
    ("unanswerable_rules", "Within how many days must a Data Fiduciary respond to a grievance?"),
    ("unanswerable_rules", "After how many months of user inactivity is the specified purpose deemed to be no longer served?"),
    ("unanswerable_rules", "Which countries has the Central Government restricted for the transfer of personal data?"),
    ("unanswerable_rules", "What annual turnover makes a company a Significant Data Fiduciary?"),
    ("unanswerable_rules", "What is the fee for filing an appeal before the Appellate Tribunal?"),
    ("unanswerable_rules", "How many Members does the Data Protection Board of India have?"),
    ("unanswerable_rules", "What is the monthly salary of the Chairperson of the Board?"),
    ("unanswerable_rules", "Which technical method must be used to verify a parent's consent?"),
    ("unanswerable_ood", "What is the best biryani recipe?"),
    ("unanswerable_ood", "Who won the 2011 Cricket World Cup?"),
    ("unanswerable_ood", "Write a Python function that reverses a list."),
    ("unanswerable_ood", "What is the capital gains tax rate on listed shares in India?"),
    ("unanswerable_ood", "Which laptop should I buy for under 50,000 rupees?"),
    ("unanswerable_ood", "What is the GST rate on restaurant food?"),
]

# Translations of English items, keyed by the source item's evidence phrase.
TRANSLATIONS = [
    ("hi", "has not completed the age of eighteen years", "डीपीडीपी अधिनियम के तहत 'बालक' कौन है?"),
    ("hi", "determines the purpose and means of processing", "डेटा फिड्यूशरी कौन होता है?"),
    ("hi", "free, specific, informed, unconditional and unambiguous", "वैध सहमति के लिए कौन-सी शर्तें पूरी होनी चाहिए?"),
    ("hi", "right to withdraw her consent at any time", "क्या डेटा प्रिंसिपल अपनी सहमति वापस ले सकती है?"),
    ("hi", "give the Board and each affected Data Principal", "व्यक्तिगत डेटा उल्लंघन होने पर डेटा फिड्यूशरी को किसे सूचित करना होगा?"),
    ("hi", "as soon as it is reasonable to assume that the specified purpose is no longer being served", "डेटा फिड्यूशरी को व्यक्तिगत डेटा कब मिटाना चाहिए?"),
    ("hi", "obtain verifiable consent of the parent", "बच्चे के व्यक्तिगत डेटा को प्रोसेस करने से पहले किसकी सहमति चाहिए?"),
    ("hi", "targeted advertising directed at children", "डीपीडीपी अधिनियम की धारा 9(3) किस पर रोक लगाती है?"),
    ("hi", "two hundred and fifty crore rupees", "उचित सुरक्षा उपाय न करने पर अधिकतम जुर्माना कितना है?"),
    ("hi", "in the event of death or incapacity of the Data Principal", "क्या डेटा प्रिंसिपल अपने अधिकारों के प्रयोग के लिए किसी को नामित कर सकती है?"),
    ("hi", "within a period of sixty days", "बोर्ड के आदेश के विरुद्ध अपील दायर करने की समय-सीमा क्या है?"),
    ("hi", "exhaust the opportunity of redressing her grievance", "क्या डेटा प्रिंसिपल अपनी शिकायत सीधे बोर्ड के पास ले जा सकती है?"),
    ("mr", "has not completed the age of eighteen years", "डीपीडीपी कायद्यानुसार 'बालक' म्हणजे कोण?"),
    ("mr", "identifiable by or in relation to such data", "'वैयक्तिक डेटा' म्हणजे काय?"),
    ("mr", "right to withdraw her consent at any time", "डेटा प्रिन्सिपल आपली संमती मागे घेऊ शकते का?"),
    ("mr", "give the Board and each affected Data Principal", "वैयक्तिक डेटाचा भंग झाल्यास डेटा फिड्युशरीने कोणाला कळवावे?"),
    ("mr", "obtain verifiable consent of the parent", "मुलाच्या वैयक्तिक डेटावर प्रक्रिया करण्यापूर्वी कोणाची संमती घ्यावी लागते?"),
    ("mr", "additional obligations in relation to children", "मुलांसंबंधीच्या जबाबदाऱ्यांचे उल्लंघन केल्यास कमाल दंड किती आहे?"),
    ("mr", "establish an effective mechanism to redress the grievances", "डेटा फिड्युशरीने तक्रार निवारण यंत्रणा ठेवणे आवश्यक आहे का?"),
    ("mr", "restrict the transfer of personal data", "डीपीडीपी कायद्याचे कलम 16(1) भारताबाहेर वैयक्तिक डेटा हस्तांतरित करण्याबद्दल काय सांगते?"),
]
DEV_SIZE = 60


def load() -> list[dict]:
    items = []
    for line in EN.strip().splitlines():
        kind, prov, q, a, phrase = [x.strip() for x in line.split("|")]
        items.append({"type": kind, "provision": prov, "question": q, "answer": a, "phrase": phrase, "lang": "en", "answerable": True})
    by_phrase = {i["phrase"]: i for i in items}
    for kind, q in UNANSWERABLE:
        items.append({"type": kind, "provision": None, "question": q, "phrase": None, "lang": "en", "answerable": False,
                      "answer": "The Act does not answer this." if kind == "unanswerable_rules" else "Out of scope."})
    for i, it in enumerate(items, 1):
        it["id"], it["source"] = f"EN{i:03d}", None
    for n, (lang, phrase, q) in enumerate(TRANSLATIONS, 1):
        src = by_phrase[phrase]
        items.append({**src, "id": f"{lang.upper()}{n:02d}", "question": q, "lang": lang, "source": src["id"]})
    # Development / test split by source item, so a translation stays with its English original.
    groups = [it for it in items if it["source"] is None]
    random.Random(2023).shuffle(groups)
    dev, size = set(), 0
    for g in groups:
        n = 1 + sum(1 for it in items if it["source"] == g["id"])
        if size + n <= DEV_SIZE:
            dev.add(g["id"])
            size += n
    for it in items:
        it["split"] = "dev" if (it["source"] or it["id"]) in dev else "test"
    return items


def dataset_hash(items: list[dict]) -> str:
    return hashlib.sha256("\n".join(f"{i['id']}|{i['question']}|{i['phrase']}|{i['split']}" for i in items).encode()).hexdigest()[:12]


def validate(items: list[dict], st: Statute) -> list[str]:
    """Each evidence phrase must occur in the Act, and only inside its gold provision."""
    units = [(u.provision, norm((u.lead + " " + u.text) if u.clause else u.text)) for u in st.units(1)]  # clause level
    units.append(("Schedule", norm(st.schedule)))
    problems = []
    for it in items:
        if not it["answerable"] or it["lang"] != "en":
            continue
        phrase, gold = norm(it["phrase"]), it["provision"]
        where = [p for p, text in units if phrase in text]
        if not where:
            problems.append(f"{it['id']} {gold}: phrase not found: {it['phrase']!r}")
        elif any(not (p == gold or p.startswith(gold + "(")) for p in where):
            problems.append(f"{it['id']} {gold}: phrase also occurs in {sorted(set(where) - {gold})}: {it['phrase']!r}")
    return problems


def relevant(chunk_text: str, item: dict) -> bool:
    return bool(item["phrase"]) and norm(item["phrase"]) in norm(chunk_text)
