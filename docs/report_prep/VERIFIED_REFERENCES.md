# Verified References for the Project Report

Checked on 2026-10-27 against the Crossref DOI registry (authors, title,
venue, volume, pages and year read from the registered record) and, for items
without a DOI, against the publisher or proceedings page. Source lists merged:
Person A's `docs/literature_references.md` (branch `literature-survey-person-a`,
commit e53b66b) and the reference list in `docs/report/ieee_paper_content.md`.

Final numbers [1], [2], ... are assigned when the report is written, in order
of first citation (IEEE style). The `K` keys below are working labels only.

## 1. Corrections to Person A's list

| Entry | Problem found | Correction |
|---|---|---|
| A[8] CNN-LSTM hybrid, *IEEE Access* 10, 99837-99849 (2022) | Author given as "J. Kim et al." The registered record has different authors | **A. Halbouni, T. S. Gunawan, M. H. Habaebi, M. Halbouni, M. Kartiwi, R. Ahmad.** Title, volume, pages and DOI were right. The survey text and matrix also say "Kim et al." and must say "Halbouni et al." |
| A[7] Vinayakumar | Flagged "metadata to verify" | Verified: six authors, *IEEE Access* 7, 41525-41550, 2019, DOI 10.1109/ACCESS.2019.2895334 |
| A[13] TON_IoT | Flagged; no authors, venue or pages | Verified: Alsaedi, Moustafa, Tari, Mahmood, Anwar; *IEEE Access* 8, 165130-165150, 2020 |
| A[18] E-XAI | Flagged; no authors | Verified: Arreche, Guntur, Roberts, Abdallah |
| A[19] LIME/SHAP on MLP | Flagged; no authors | Verified: Gaspar, Silva, Silva |
| A[20] XAI survey | Flagged; no authors | Verified: Nascita, Aceto, Ciuonzo, Montieri, Persico, Pescapè; vol. 27, no. 5, 2025 |
| A[21] XAI for NIDS, *High-Confidence Computing* | Flagged; existence doubtful | Exists: single author D. Manivannan, vol. 6, no. 4, article 100423, 2026 |
| A[25] Ferrag et al. | Flagged; no venue or DOI | Verified: Ferrag, Maglaras, Moschoyiannis, Janicke; *J. Inf. Secur. Appl.* 50, 102419, 2020, DOI 10.1016/j.jisa.2019.102419 |
| MU-IoT (missing in both lists) | Placeholder | Found: Clinton and Hoque, *IEEE Access* 12, 166068-166092, 2024, DOI 10.1109/ACCESS.2024.3494052 |

All other entries ([1]-[6], [9]-[12], [14]-[17], [22]-[24]) matched their DOIs.

## 2. Merged list (30 references, IEEE style)

K1. A. L. Buczak and E. Guven, "A survey of data mining and machine learning methods for cyber security intrusion detection," *IEEE Commun. Surveys Tuts.*, vol. 18, no. 2, pp. 1153-1176, 2016, doi: 10.1109/COMST.2015.2494502.

K2. R. Sommer and V. Paxson, "Outside the closed world: On using machine learning for network intrusion detection," in *Proc. IEEE Symp. Security Privacy*, 2010, pp. 305-316, doi: 10.1109/SP.2010.25.

K3. A. Khraisat, I. Gondal, P. Vamplew, and J. Kamruzzaman, "Survey of intrusion detection systems: Techniques, datasets and challenges," *Cybersecurity*, vol. 2, Art. no. 20, 2019, doi: 10.1186/s42400-019-0038-7.

K4. P. García-Teodoro, J. Díaz-Verdejo, G. Maciá-Fernández, and E. Vázquez, "Anomaly-based network intrusion detection: Techniques, systems and challenges," *Comput. Secur.*, vol. 28, nos. 1-2, pp. 18-28, 2009, doi: 10.1016/j.cose.2008.08.003.

K5. N. Shone, T. N. Ngoc, V. D. Phai, and Q. Shi, "A deep learning approach to network intrusion detection," *IEEE Trans. Emerg. Topics Comput. Intell.*, vol. 2, no. 1, pp. 41-50, 2018, doi: 10.1109/TETCI.2017.2772792.

K6. C. Yin, Y. Zhu, J. Fei, and X. He, "A deep learning approach for intrusion detection using recurrent neural networks," *IEEE Access*, vol. 5, pp. 21954-21961, 2017, doi: 10.1109/ACCESS.2017.2762418.

K7. R. Vinayakumar, M. Alazab, K. P. Soman, P. Poornachandran, A. Al-Nemrat, and S. Venkatraman, "Deep learning approach for intelligent intrusion detection system," *IEEE Access*, vol. 7, pp. 41525-41550, 2019, doi: 10.1109/ACCESS.2019.2895334.

K8. A. Halbouni, T. S. Gunawan, M. H. Habaebi, M. Halbouni, M. Kartiwi, and R. Ahmad, "CNN-LSTM: Hybrid deep neural network for network intrusion detection system," *IEEE Access*, vol. 10, pp. 99837-99849, 2022, doi: 10.1109/ACCESS.2022.3206425.

K9. I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, "Toward generating a new intrusion detection dataset and intrusion traffic characterization," in *Proc. 4th Int. Conf. Inf. Syst. Security Privacy (ICISSP)*, 2018, pp. 108-116, doi: 10.5220/0006639801080116.

K10. N. Moustafa and J. Slay, "UNSW-NB15: A comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set)," in *Proc. Mil. Commun. Inf. Syst. Conf. (MilCIS)*, 2015, pp. 1-6, doi: 10.1109/MilCIS.2015.7348942.

K11. Y. Meidan *et al.*, "N-BaIoT: Network-based detection of IoT botnet attacks using deep autoencoders," *IEEE Pervasive Comput.*, vol. 17, no. 3, pp. 12-22, 2018, doi: 10.1109/MPRV.2018.03367731.

K12. N. Koroniotis, N. Moustafa, E. Sitnikova, and B. Turnbull, "Towards the development of realistic botnet dataset in the Internet of Things for network forensic analytics: Bot-IoT dataset," *Future Gener. Comput. Syst.*, vol. 100, pp. 779-796, 2019, doi: 10.1016/j.future.2019.05.041.

K13. A. Alsaedi, N. Moustafa, Z. Tari, A. Mahmood, and A. Anwar, "TON_IoT telemetry dataset: A new generation dataset of IoT and IIoT for data-driven intrusion detection systems," *IEEE Access*, vol. 8, pp. 165130-165150, 2020, doi: 10.1109/ACCESS.2020.3022862.

K14. M. Ring, S. Wunderlich, D. Scheuring, D. Landes, and A. Hotho, "A survey of network-based intrusion detection data sets," *Comput. Secur.*, vol. 86, pp. 147-167, 2019, doi: 10.1016/j.cose.2019.06.005.

K15. M. Tavallaee, E. Bagheri, W. Lu, and A. A. Ghorbani, "A detailed analysis of the KDD CUP 99 data set," in *Proc. IEEE Symp. Comput. Intell. Security Defense Appl.*, 2009, pp. 1-6, doi: 10.1109/CISDA.2009.5356528.

K16. S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," in *Proc. Adv. Neural Inf. Process. Syst. 30 (NeurIPS)*, 2017, pp. 4765-4774. [pages not re-checked in this pass]

K17. M. T. Ribeiro, S. Singh, and C. Guestrin, "'Why should I trust you?': Explaining the predictions of any classifier," in *Proc. 22nd ACM SIGKDD Int. Conf. Knowl. Discovery Data Mining*, 2016, pp. 1135-1144, doi: 10.1145/2939672.2939778.

K18. O. Arreche, T. R. Guntur, J. W. Roberts, and M. Abdallah, "E-XAI: Evaluating black-box explainable AI frameworks for network intrusion detection," *IEEE Access*, vol. 12, pp. 23954-23988, 2024, doi: 10.1109/ACCESS.2024.3365140.

K19. D. Gaspar, P. Silva, and C. Silva, "Explainable AI for intrusion detection systems: LIME and SHAP applicability on multi-layer perceptron," *IEEE Access*, vol. 12, pp. 30164-30175, 2024, doi: 10.1109/ACCESS.2024.3368377.

K20. A. Nascita, G. Aceto, D. Ciuonzo, A. Montieri, V. Persico, and A. Pescapè, "A survey on explainable artificial intelligence for Internet traffic classification and prediction, and intrusion detection," *IEEE Commun. Surveys Tuts.*, vol. 27, no. 5, pp. 3165-3198, 2025, doi: 10.1109/COMST.2024.3504955.

K21. D. Manivannan, "A comprehensive analysis of explainable AI-driven machine learning techniques for network intrusion detection systems," *High-Confidence Comput.*, vol. 6, no. 4, Art. no. 100423, 2026, doi: 10.1016/j.hcc.2026.100423.

K22. S. Hochreiter and J. Schmidhuber, "Long short-term memory," *Neural Comput.*, vol. 9, no. 8, pp. 1735-1780, 1997, doi: 10.1162/neco.1997.9.8.1735.

K23. Y. LeCun, L. Bottou, Y. Bengio, and P. Haffner, "Gradient-based learning applied to document recognition," *Proc. IEEE*, vol. 86, no. 11, pp. 2278-2324, Nov. 1998, doi: 10.1109/5.726791.

K24. A. A. Diro and N. Chilamkurti, "Distributed attack detection scheme using deep learning approach for Internet of Things," *Future Gener. Comput. Syst.*, vol. 82, pp. 761-768, 2018, doi: 10.1016/j.future.2017.08.043.

K25. M. A. Ferrag, L. Maglaras, S. Moschoyiannis, and H. Janicke, "Deep learning for cyber security intrusion detection: Approaches, datasets, and comparative study," *J. Inf. Secur. Appl.*, vol. 50, Art. no. 102419, 2020, doi: 10.1016/j.jisa.2019.102419.

K26. G. Engelen, V. Rimmer, and W. Joosen, "Troubleshooting an intrusion detection dataset: The CICIDS2017 case study," in *Proc. IEEE Security Privacy Workshops (SPW)*, 2021, pp. 7-12, doi: 10.1109/SPW53761.2021.00009.

K27. A. H. Lashkari, G. Draper-Gil, M. S. I. Mamun, and A. A. Ghorbani, "Characterization of Tor traffic using time based features," in *Proc. 3rd Int. Conf. Inf. Syst. Security Privacy (ICISSP)*, 2017, pp. 253-262, doi: 10.5220/0006105602530262. (The CICFlowMeter reference.)

K28. D. Arp *et al.*, "Dos and don'ts of machine learning in computer security," in *Proc. 31st USENIX Security Symp.*, 2022, pp. 3971-3988. [pages from one USENIX listing; arXiv:2010.09470]

K29. L. Breiman, "Random forests," *Mach. Learn.*, vol. 45, no. 1, pp. 5-32, 2001, doi: 10.1023/A:1010933404324.

K30. U. B. Clinton and N. Hoque, "MU-IoT: A new IoT intrusion dataset for network and application layer attacks analysis," *IEEE Access*, vol. 12, pp. 166068-166092, 2024, doi: 10.1109/ACCESS.2024.3494052.

## 3. Open points

- **Check before the final copy:** K16 pages and K28 pages (one source each).
  Entries K3 and K21 use article numbers instead of pages, which is correct
  for those journals.
- **MU-IoT description to reconcile (ask Person A).** Manipur University's
  dataset page (https://manipuruniv.ac.in/CSDmuIOTdataset/) describes 121
  flow features, 3 label fields and over 34.8 million records. Our pipeline
  used 3,936,753 rows, 38 features and 7 classes. Chapter 3 must say how our
  data was derived from the published dataset (subset, feature ranking from
  the paper's Table 8, class grouping).
- **Person A's survey text** still says the response component is
  "recommendation-based/simulated" and "should not be described as blocking
  live traffic". That is out of date: the system adds real Windows Firewall
  rules (IPS-lite). The report will say so.
- **Per-paper findings.** Person A recorded relevance only. Chapter 2 will
  describe each paper's method and limitation as stated in its abstract, and
  will not quote numeric results that were not checked in the original paper.
