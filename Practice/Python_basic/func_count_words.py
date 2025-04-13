def count_words(sentence):
    print(f'단어 수: {len(sentence.split())}')

sent = input('문자열:')
count_words(sent)