wget https://qoiformat.org/qoi_test_images.zip
unzip qoi_test_images.zip
for qoi in qoi_test_images/*.qoi; do
   ref=${qoi:0:${#qoi}-3}"png"
   python test.py -q $qoi -r $ref
done
