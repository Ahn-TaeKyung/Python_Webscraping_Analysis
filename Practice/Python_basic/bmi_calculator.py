kg = float(input('체중(kg):'))
m = float(input('키(cm):')) / 100
print(f'BMI: {kg/(m**2):.1f}')